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

    const loaderInterval = setInterval(() => {
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
                body: JSON.stringify({catalogFile: this.formData.catalogFile})
            });
            const data = await resp.json();
            if (data.ok && data.status === 'processing') {
                // Poll status
                const checkStatus = async () => {
                    try {
                        const statusResp = await fetch('/api/plugins/avender/parse_catalog_status_api', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({})
                        });
                        const statusData = await statusResp.json();
                        if (statusData.status === 'done') {
                            this.formData.catalogItems = statusData.items;
                            clearInterval(loaderInterval);
                            this.catalogLoading = false;
                            this.requestUpdate();
                        } else if (statusData.status === 'error') {
                            this.catalogError = statusData.error || "Error al extraer ítems.";
                            clearInterval(loaderInterval);
                            this.catalogLoading = false;
                            this.requestUpdate();
                        } else {
                            // Keep waiting
                            setTimeout(checkStatus, 3000);
                        }
                    } catch (err) {
                        this.catalogError = "Error de red al consultar el estado.";
                        clearInterval(loaderInterval);
                        this.catalogLoading = false;
                        this.requestUpdate();
                    }
                };
                setTimeout(checkStatus, 3000);
            } else if (data.ok) {
                // Sync fallback
                this.formData.catalogItems = data.items;
                clearInterval(loaderInterval);
                this.catalogLoading = false;
                this.requestUpdate();
            } else {
                this.catalogError = data.error || "Error al procesar el archivo.";
                clearInterval(loaderInterval);
                this.catalogLoading = false;
                this.requestUpdate();
            }
        } catch(err) {
            this.catalogError = "Error de conexión al procesar el archivo.";
            clearInterval(loaderInterval);
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
        file: this.chatFile
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
export async function submitSetup() {
    if (!this.formData.whatsappNumber || !this.formData.tradeName) {
        this.errorMessage = "Por favor completa los campos obligatorios.";
        return;
    }

    this.loading = true;
    this.errorMessage = '';
    this.requestUpdate();

    try {
        const resp = await fetch('/api/plugins/avender/onboarding_api', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(this.formData)
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
    this.qrStatus = 'loading';
    this.qrDataUrl = null;
    this.requestUpdate();

    this.qrPollTimer = setInterval(async () => {
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
                this.qrStatus = 'connected';
            } else if (data.qr) {
                this.qrStatus = 'qr_ready';
                this.qrDataUrl = data.qr;
            }
        } catch (err) {
            console.warn('QR poll error:', err);
        }
        this.requestUpdate();
    }, 3000);
}
