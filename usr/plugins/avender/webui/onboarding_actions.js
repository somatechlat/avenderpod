export async function handleMapClick(lat, lng) {
    if (this.mapMarker) {
        this.mapMarker.setLatLng([lat, lng]);
    } else {
        this.mapMarker = L.marker([lat, lng]).addTo(this.mapInstance);
    }
    this.mapInstance.setView([lat, lng], 16);

    try {
        this.formData.headquarters = "Buscando dirección...";
        this.requestUpdate();
        const resp = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`);
        const data = await resp.json();
        if (data && data.display_name) {
            const parts = data.display_name.split(',');
            this.formData.headquarters = `${parts[0]}, ${parts[1] || ''}`.trim();
        } else {
            this.formData.headquarters = `GPS: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
        }
    } catch (err) {
        this.formData.headquarters = `GPS: ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
    }
    this.requestUpdate();
}

export function useMyLocation() {
    if (!navigator.geolocation) {
        alert("Tu navegador no soporta geolocalización.");
        return;
    }
    this.formData.headquarters = "Obteniendo tu ubicación GPS...";
    this.requestUpdate();
    navigator.geolocation.getCurrentPosition(
        (position) => {
            this.handleMapClick(position.coords.latitude, position.coords.longitude);
        },
        (error) => {
            alert("No se pudo obtener la ubicación. Por favor, toca el mapa manualmente.");
            this.formData.headquarters = "";
            this.requestUpdate();
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

export function initMap() {
    if (this.mapInstance) {
        this.mapInstance.invalidateSize();
        return;
    }
    this.mapInstance = L.map('map').setView([-0.180653, -78.467838], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(this.mapInstance);

    this.mapInstance.on('click', (e) => {
        this.handleMapClick(e.latlng.lat, e.latlng.lng);
    });
}

export async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    // Client-side file size limit: 25MB
    if (file.size > 25 * 1024 * 1024) {
        this.catalogError = "El archivo es demasiado grande. El límite es de 25 MB.";
        this.requestUpdate();
        return;
    }
    this.catalogFileName = file.name;
    this.catalogLoading = true;
    this.catalogError = '';
    this.loadingMessage = "Leyendo archivo original...";
    this.requestUpdate();

    let msgIndex = 0;
    const messages = [
        "Leyendo archivo original...",
        "Analizando la estructura del documento...",
        "Ejecutando Inteligencia Artificial...",
        "Extrayendo nombres, precios y descripciones...",
        "Estructurando el catálogo final..."
    ];

    this.loaderInterval = setInterval(() => {
        msgIndex = (msgIndex + 1) % messages.length;
        this.loadingMessage = messages[msgIndex];
        this.requestUpdate();
    }, 3000);

    const reader = new FileReader();
    reader.onload = async (e) => {
        this.formData.catalogFile = {
            name: file.name,
            content: e.target.result // Base64 data URI
        };

        try {
            const resp = await fetch('/api/plugins/avender/parse_catalog_api', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    catalogFile: this.formData.catalogFile,
                    archetype: this.formData.archetype || 'restaurant',
                    setupToken: this.setupToken || ''
                })
            });
            let data = null;
            try {
                data = await resp.json();
            } catch (jsonErr) {
                data = {
                    ok: false,
                    error: `Respuesta inválida del servidor (${resp.status}).`
                };
            }

            if (!resp.ok && data && !data.error) {
                data.error = `Error del servidor (${resp.status}).`;
            }
            if (data.ok) {
                const items = data.items || [];
                this.formData.catalogItems = items;
                clearInterval(this.loaderInterval);
                this.catalogLoading = false;
                // Open review modal when items were extracted from PDF
                if (items.length > 0) {
                    this.showCatalogModal = true;
                }
                this.requestUpdate();
            } else {
                this.catalogError = data.error || "Error al procesar el archivo.";
                clearInterval(this.loaderInterval);
                this.catalogLoading = false;
                this.requestUpdate();
            }
        } catch(err) {
            this.catalogError = "Error de conexión al procesar el archivo.";
            clearInterval(this.loaderInterval);
            this.catalogLoading = false;
            this.requestUpdate();
        }
    };
    reader.readAsDataURL(file);
}

export function handleItemImageUpload(event, index) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        this.formData.catalogItems[index].image = e.target.result;
        this.requestUpdate();
    };
    reader.readAsDataURL(file);
}

export function removeCatalogItem(index) {
    this.formData.catalogItems.splice(index, 1);
    this.requestUpdate();
}

export function addManualItem() {
    if (!this.newItem.name || !this.newItem.price) return;
    this.formData.catalogItems.push({...this.newItem});
    this.newItem = { name: '', description: '', price: '' };
    this.requestUpdate();
}

export function loadPresets() {
    if (this.formData.catalogItems.length > 0) return; // Don't overwrite if they already have items

    const presets = {
        'restaurant': [
            { name: 'Hamburguesa Clásica', description: 'Con queso, lechuga, tomate y papas fritas.', price: 8.50 },
            { name: 'Pizza Pepperoni Familiar', description: 'Masa artesanal con doble queso y pepperoni.', price: 12.00 },
            { name: 'Ensalada César', description: 'Lechuga romana, crutones, pollo y aderezo césar.', price: 7.00 },
            { name: 'Gaseosa 500ml', description: 'Bebida fría a elección.', price: 1.50 }
        ],
        'retail': [
            { name: 'Camiseta Básica Algodón', description: 'Camiseta 100% algodón, varios colores.', price: 15.00 },
            { name: 'Pantalón Jean Clásico', description: 'Corte recto, mezclilla duradera.', price: 35.00 },
            { name: 'Chaqueta Impermeable', description: 'Chaqueta ligera para lluvia.', price: 45.00 },
            { name: 'Zapatos Deportivos', description: 'Calzado cómodo para correr.', price: 60.00 }
        ],
        'groceries': [
            { name: 'Leche Entera 1L', description: 'Leche de vaca pasteurizada.', price: 1.20 },
            { name: 'Huevos Cubeta (30)', description: 'Cubeta de huevos grandes.', price: 4.50 },
            { name: 'Arroz 2kg', description: 'Arroz blanco de grano largo.', price: 3.00 },
            { name: 'Pan de Molde', description: 'Pan blanco rebanado.', price: 2.50 }
        ],
        'beauty': [
            { name: 'Corte de Cabello', description: 'Corte estilizado según solicitud.', price: 10.00 },
            { name: 'Manicure Básico', description: 'Limpieza y pintura tradicional.', price: 15.00 },
            { name: 'Tinte de Cabello', description: 'Aplicación de color y lavado.', price: 40.00 },
            { name: 'Masaje Relajante', description: 'Masaje corporal de 45 minutos.', price: 35.00 }
        ],
        'tech': [
            { name: 'Cable USB-C a USB-C', description: 'Cable de carga rápida de 1.5m.', price: 8.00 },
            { name: 'Audífonos Inalámbricos', description: 'Auriculares Bluetooth con cancelación de ruido.', price: 45.00 },
            { name: 'Mica de Vidrio', description: 'Protector de pantalla para celular.', price: 5.00 },
            { name: 'Cargador Rápido 20W', description: 'Adaptador de pared USB-C.', price: 15.00 }
        ],
        'services': [
            { name: 'Asesoría Inicial', description: 'Reunión de evaluación de 1 hora.', price: 50.00 },
            { name: 'Mantenimiento Preventivo', description: 'Revisión técnica estándar.', price: 80.00 },
            { name: 'Servicio de Urgencia', description: 'Atención prioritaria 24/7.', price: 120.00 }
        ],
        'doctor': [
            { name: 'Consulta General', description: 'Evaluación médica preventiva.', price: 40.00 },
            { name: 'Consulta Especialidad', description: 'Evaluación por médico especialista.', price: 60.00 },
            { name: 'Examen de Sangre Básico', description: 'Biometría hemática completa.', price: 25.00 },
            { name: 'Certificado Médico', description: 'Emisión de certificado de salud.', price: 15.00 }
        ],
        'pharmacy': [
            { name: 'Paracetamol 500mg', description: 'Caja x20 tabletas.', price: 3.50 },
            { name: 'Vitamina C 1g', description: 'Tubo efervescente x10.', price: 5.00 },
            { name: 'Alcohol Antiséptico', description: 'Botella de 500ml.', price: 2.50 },
            { name: 'Ibuprofeno 400mg', description: 'Caja x10 cápsulas.', price: 4.00 }
        ],
        'hardware': [
            { name: 'Martillo de Acero', description: 'Martillo con mango de goma.', price: 12.00 },
            { name: 'Juego de Destornilladores', description: 'Set de 6 piezas cruz y plano.', price: 18.00 },
            { name: 'Cinta Métrica 5m', description: 'Flexómetro metálico.', price: 6.00 },
            { name: 'Pegamento de Contacto', description: 'Lata de 250ml.', price: 4.50 }
        ],
        'liquor': [
            { name: 'Cerveza Nacional 6-Pack', description: 'Botellas de 330ml.', price: 7.50 },
            { name: 'Vino Tinto Reserva', description: 'Botella de 750ml, Cabernet.', price: 22.00 },
            { name: 'Whisky 12 Años', description: 'Botella de 750ml.', price: 45.00 },
            { name: 'Hielo (Bolsa 2kg)', description: 'Bolsa de cubos de hielo.', price: 2.00 }
        ],
        'cbd': [
            { name: 'Gotas CBD 5%', description: 'Frasco gotero de 10ml.', price: 35.00 },
            { name: 'Crema Relajante Muscular', description: 'Bálsamo tópico con CBD.', price: 25.00 },
            { name: 'Gomitas Relajantes', description: 'Frasco de 30 gomitas.', price: 30.00 }
        ],
        'other': [
            { name: 'Producto Genérico 1', description: 'Descripción de prueba.', price: 10.00 },
            { name: 'Servicio Básico', description: 'Atención general.', price: 25.00 }
        ]
    };

    const ind = this.formData.archetype;
    if (presets[ind]) {
        this.formData.catalogItems = [...presets[ind]];
        this.requestUpdate();
    }
}



export function handleCopilotFile(event) {
    const file = event.target.files[0];
    if (!file) return;
    this.chatFileName = file.name;
    const reader = new FileReader();
    reader.onload = (e) => {
        this.chatFile = {
            name: file.name,
            content: e.target.result
        };
        this.requestUpdate();
    };
    reader.readAsDataURL(file);
}

export async function sendChat() {
    if ((!this.chatInput.trim() && !this.chatFile) || this.chatLoading) return;

    const userText = this.chatInput || (this.chatFile ? "[Archivo adjunto]" : "");
    this.chatMessages = [...this.chatMessages, {role: 'user', content: userText}];

    const payload = {
        question: this.chatInput,
        file: this.chatFile,
        setupToken: this.setupToken || ''
    };

    this.chatInput = '';
    this.chatFile = null;
    this.chatFileName = '';
    this.chatLoading = true;

    this.scrollToBottom();

    try {
        const resp = await fetch('/api/plugins/avender/wizard_chat_api', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.ok) {
            this.chatMessages = [...this.chatMessages, {role: 'assistant', content: data.answer}];
        } else {
            this.chatMessages = [...this.chatMessages, {role: 'assistant', content: "Hubo un problema. Intenta nuevamente."}];
        }
    } catch (e) {
        this.chatMessages = [...this.chatMessages, {role: 'assistant', content: "Error de conexión."}];
    } finally {
        this.chatLoading = false;
        this.scrollToBottom();
    }
}

export function scrollToBottom() {
    setTimeout(() => {
        const container = document.getElementById('chat-container');
        if(container) container.scrollTop = container.scrollHeight;
    }, 50);
}

export function updateField(field, value) {
    this.formData[field] = value;
    this.requestUpdate();
}

export function formatWhatsAppNumber(raw) {
    // Ecuador +593 auto-prefix: strip everything except digits,
    // then prepend +593 if there is no leading +.
    let digits = raw.replace(/[^0-9]/g, '');
    if (!raw.startsWith('+')) {
        if (digits.startsWith('593')) {
            digits = '+' + digits;
        } else if (digits.startsWith('0')) {
            digits = '+593' + digits.slice(1);
        } else {
            digits = '+593' + digits;
        }
    } else {
        digits = '+' + digits;
    }
    return digits;
}

export function getStepValidation(step = this.step) {
    const requiredByStep = {
        1: [
            ["idType", "Tipo de Documento"],
            ["idNumber", "Número de Identificación"],
            ["tradeName", "Nombre Comercial"]
        ],
        2: [["headquarters", "Dirección Matriz"]],
        3: [["archetype", "Giro de tu negocio"]],
        5: [
            ["whatsappNumber", "Número de WhatsApp del Negocio"],
            ["adminPassword", "Contraseña de Administrador"]
        ]
    };

    const missing = [];
    const current = requiredByStep[step] || [];
    for (const [field, label] of current) {
        const value = this.formData[field];
        if (typeof value === "string") {
            if (!value.trim()) missing.push(label);
            continue;
        }
        if (!value) missing.push(label);
    }

    // Step 1: RUC / Cédula length validation
    if (step === 1) {
        const idType = this.formData.idType;
        const idNum = (this.formData.idNumber || '').trim();
        if (idType === 'RUC' && idNum.length !== 13) {
            missing.push("RUC debe tener 13 dígitos");
        }
        if (idType === 'CEDULA' && idNum.length !== 10) {
            missing.push("Cédula debe tener 10 dígitos");
        }
    }

    // Step 3: at least one catalog item
    if (step === 3) {
        const count = (this.formData.catalogItems || []).length;
        if (count < 1) {
            missing.push("Al menos 1 producto en el catálogo");
        }
    }

    if (step === 5 && this.formData.restrictAccess) {
        const hasAllowedNumbers = this.formData.allowedNumbers
            .split(",")
            .map(n => n.trim())
            .filter(Boolean).length > 0;
        if (!hasAllowedNumbers) {
            missing.push("Lista Blanca (al menos un número)");
        }
    }

    // Step 5: WhatsApp format validation
    if (step === 5) {
        const wa = (this.formData.whatsappNumber || '').trim();
        if (!/^\+[1-9]\d{7,14}$/.test(wa)) {
            missing.push("Número de WhatsApp válido (ej: +593999999999)");
        }
        if (this.formData.adminPassword && this.formData.adminPassword.length < 8) {
            missing.push("Contraseña de Administrador (mínimo 8 caracteres)");
        }
    }

    return {
        valid: missing.length === 0,
        missing
    };
}

export function goToNextStep() {
    if (this.step >= 6) return;
    const validation = this.getStepValidation(this.step);
    if (!validation.valid) {
        this.errorMessage = `Completa los campos requeridos: ${validation.missing.join(", ")}`;
        this.requestUpdate();
        return;
    }
    this.errorMessage = "";
    this.step += 1;
    this.requestUpdate();
}

export async function submitSetup() {
    if (this.loading) return; // Guard against double-submit
    const missing = [];
    for (let step = 1; step <= 5; step += 1) {
        const validation = this.getStepValidation(step);
        if (!validation.valid) {
            missing.push(...validation.missing);
        }
    }
    if (missing.length > 0) {
        this.errorMessage = `Completa los campos requeridos: ${[...new Set(missing)].join(", ")}`;
        return;
    }

    this.loading = true;
    this.errorMessage = '';
    this.requestUpdate();

    try {
        const resp = await fetch('/api/plugins/avender/onboarding_api', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                ...this.formData,
                setupToken: this.setupToken || ''
            })
        });
        const data = await resp.json();

        if (data.ok) {
            this.step = 7;
            this.pollQrCode(); // Start polling QR
        } else {
            this.errorMessage = data.error || "Hubo un error al guardar.";
        }
    } catch (err) {
        this.errorMessage = "Error de conexión con el servidor.";
    } finally {
        this.loading = false;
        this.requestUpdate();
    }
}

export async function pollQrCode() {
    // Clear any existing poll before starting a new one
    if (this.qrPollTimer) clearInterval(this.qrPollTimer);
    this.qrStatus = 'loading';
    this.qrDataUrl = null;
    this.requestUpdate();

    const doPoll = async () => {
        try {
            const response = await fetch('/api/plugins/_whatsapp_integration/qr_code', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            });
            if (!response.ok) {
                console.warn('QR endpoint returned', response.status);
                this.requestUpdate();
                return;
            }
            const data = await response.json();

            if (data.status === 'connected') {
                clearInterval(this.qrPollTimer);
                this.qrPollTimer = null;
                this.qrStatus = 'connected';
            } else if (data.qr) {
                this.qrStatus = 'qr_ready';
                this.qrDataUrl = data.qr;
            } else {
                this.qrStatus = data.status || 'loading';
            }
        } catch (err) {
            console.warn('QR poll error:', err);
        }
        this.requestUpdate();
    };

    // Poll immediately, then every 2 seconds
    doPoll();
    this.qrPollTimer = setInterval(doPoll, 2000);
}
