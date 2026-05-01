import { html } from 'https://cdn.jsdelivr.net/gh/lit/dist@3/core/lit-core.min.js';

function fieldTag(required = false) {
    return required
        ? html`<span class="ml-2 text-xs font-semibold text-red-700">Requerido</span>`
        : html`<span class="ml-2 text-xs font-semibold text-slate-500">Opcional</span>`;
}

export function renderHeader() {
    return html`
        <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-600 shadow-xl shadow-brand-500/30 mb-4 transform transition-transform hover:scale-105">
                <span class="text-2xl font-display font-bold text-white tracking-tighter">AV</span>
            </div>
            <h1 class="font-display text-3xl font-bold text-slate-900 mb-2 tracking-tight">¡A VENDER!</h1>
            <p class="text-slate-500 mt-2 font-medium">Configuración inicial de tu Asistente Virtual</p>
        </div>
    `;
}

export function renderProgressBar() {
    return html`
        <div class="w-full bg-gray-200 rounded-full h-2.5 mb-8">
            <div class="bg-indigo-600 h-2.5 rounded-full transition-all duration-500" style="width: ${Math.min((this.step / 7) * 100, 100)}%"></div>
        </div>
    `;
}

export function renderStep1() {
    return html`
        <div>
            <h2 class="text-2xl font-bold mb-2">Paso 1: Tu Negocio</h2>
            <p class="text-gray-500 mb-6 text-sm">Estos datos son privados y ayudan al asistente a conocer la empresa.</p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                    <label class="block text-base font-medium text-gray-700">Tipo de Documento ${fieldTag(true)}</label>
                    <select .value=${this.formData.idType} @change=${e => this.updateField('idType', e.target.value)} class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-3 text-base border bg-white">
                        <option value="RUC">RUC (Empresa)</option>
                        <option value="CEDULA">Cédula (Personal)</option>
                    </select>
                </div>
                <div>
                    <label class="block text-base font-medium text-gray-700">Número de Identificación ${fieldTag(true)}</label>
                    <input type="text" .value=${this.formData.idNumber} @input=${e => this.updateField('idNumber', e.target.value.replace(/\D/g, ''))} placeholder="Ej: 1712345678001" maxlength="13" class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-3 text-base border">
                    ${this.formData.idType === 'RUC' && this.formData.idNumber && this.formData.idNumber.length !== 13 ? html`<p class="text-xs text-red-600 mt-1">El RUC debe tener 13 dígitos.</p>` : ''}
                    ${this.formData.idType === 'CEDULA' && this.formData.idNumber && this.formData.idNumber.length !== 10 ? html`<p class="text-xs text-red-600 mt-1">La Cédula debe tener 10 dígitos.</p>` : ''}
                </div>
                <div class="md:col-span-2">
                    <label class="block text-base font-medium text-gray-700">Razón Social o Tu Nombre ${fieldTag(false)}</label>
                    <p class="text-xs text-gray-500 mb-1">Nombre legal registrado en el SRI o tu nombre completo.</p>
                    <input type="text" .value=${this.formData.legalName} @input=${e => this.updateField('legalName', e.target.value)} placeholder="Ej: Juan Pérez S.A." class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-3 text-base border">
                </div>
                <div class="md:col-span-2">
                    <label class="block text-base font-medium text-gray-700">Nombre Comercial ${fieldTag(true)}</label>
                    <p class="text-xs text-gray-500 mb-1">💡 Así se presentará el asistente. Ej: "Hola, soy Sofía de Burger House".</p>
                    <input type="text" .value=${this.formData.tradeName} @input=${e => this.updateField('tradeName', e.target.value)} placeholder="Ej: Burger House" class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 p-3 text-base border">
                </div>
            </div>
        </div>
    `;
}

export function renderStep2() {
    return html`
        <div>
            <h2 class="text-2xl font-bold mb-2">Paso 2: Entrega y Pagos</h2>
            <p class="text-gray-500 mb-6 text-sm">¿Cómo trabajas y cobras? Esto le dirá al asistente qué responder.</p>
            <div class="space-y-6">
                <div>
                    <label class="block text-base font-medium text-gray-700">Dirección Matriz (Tu Local) ${fieldTag(true)}</label>
                    <div class="mt-1 flex items-center mb-3 bg-indigo-50 p-3 rounded-lg border border-indigo-100 cursor-pointer" @click=${() => this.showMap = !this.showMap}>
                        <input type="checkbox" .checked=${this.showMap} class="h-6 w-6 text-indigo-600 border-gray-300 rounded pointer-events-none">
                        <span class="ml-3 block text-base text-indigo-900 font-semibold">Tocar mapa para fijar ubicación (GPS)</span>
                    </div>
                    <input type="text" .value=${this.formData.headquarters} @input=${e => this.updateField('headquarters', e.target.value)} placeholder="Ej: Av. Amazonas y Naciones Unidas, Quito" class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm p-3 text-base border">
                    ${this.showMap ? html`
                        <div class="mt-3">
                            <button type="button" @click=${this.useMyLocation} class="w-full mb-3 bg-white border-2 border-indigo-600 text-indigo-700 font-bold py-3 px-4 rounded-lg flex items-center justify-center hover:bg-indigo-50">
                                📍 Centrar en mi ubicación actual
                            </button>
                            <div id="map" class="h-64 w-full rounded-lg border-2 border-indigo-300 shadow-inner" style="z-index: 1;"></div>
                        </div>
                    ` : ''}
                </div>
                <div>
                    <label class="block text-base font-medium text-gray-700">Horarios de Atención ${fieldTag(false)}</label>
                    <div class="mt-1 flex items-center mb-3 bg-gray-50 p-3 rounded-lg border border-gray-200 cursor-pointer" @click=${() => this.updateField('useCustomHours', !this.formData.useCustomHours)}>
                        <input type="checkbox" .checked=${this.formData.useCustomHours} class="h-6 w-6 text-indigo-600 border-gray-300 rounded pointer-events-none">
                        <span class="ml-3 block text-base text-gray-900 font-semibold">Tengo horarios especiales o cierro días</span>
                    </div>
                    ${!this.formData.useCustomHours ? html`
                        <input type="text" disabled value="Lunes a Viernes 09:00 - 18:00" class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm p-3 text-base border bg-gray-100 text-gray-500 cursor-not-allowed">
                    ` : html`
                        <textarea .value=${this.formData.hours} @input=${e => this.updateField('hours', e.target.value)} rows="3" placeholder="Lunes: 9:00 - 18:00&#10;Martes: 9:00 - 18:00&#10;Sábado: Cerrado" class="block w-full rounded-lg border-gray-300 shadow-sm p-3 text-base border"></textarea>
                    `}
                </div>
                <div>
                    <label class="block text-base font-medium text-gray-700">Zonas de Envío y Costos ${fieldTag(false)}</label>
                    <textarea .value=${this.formData.deliveryRules} @input=${e => this.updateField('deliveryRules', e.target.value)} rows="3" placeholder="Norte: $2.00, Sur: $3.00." class="mt-1 block w-full rounded-lg border-gray-300 shadow-sm p-3 text-base border"></textarea>
                </div>
                <div>
                    <label class="block text-base font-medium text-gray-700 mb-2">Métodos de Pago Aceptados ${fieldTag(false)}</label>
                    <div class="space-y-3">
                        <label class="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
                            <input type="checkbox" .checked=${this.formData.payTransfer} @change=${e => this.updateField('payTransfer', e.target.checked)} class="h-6 w-6 text-indigo-600 rounded">
                            <span class="ml-3 block text-base text-gray-900">Transferencia Bancaria</span>
                        </label>
                        <label class="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
                            <input type="checkbox" .checked=${this.formData.payCash} @change=${e => this.updateField('payCash', e.target.checked)} class="h-6 w-6 text-indigo-600 rounded">
                            <span class="ml-3 block text-base text-gray-900">Efectivo</span>
                        </label>
                        <label class="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
                            <input type="checkbox" .checked=${this.formData.payLink} @change=${e => this.updateField('payLink', e.target.checked)} class="h-6 w-6 text-indigo-600 rounded">
                            <span class="ml-3 block text-base text-gray-900">Tarjeta de Crédito</span>
                        </label>
                    </div>
                </div>
                ${this.formData.payLink ? html`
                    <div class="mt-2 p-4 bg-indigo-50 rounded-lg border border-indigo-100">
                        <label class="block text-base font-medium text-indigo-900">Link de Pago universal:</label>
                        <input type="url" .value=${this.formData.paymentUrl} @input=${e => this.updateField('paymentUrl', e.target.value)} class="mt-2 block w-full rounded-lg border-gray-300 shadow-sm p-3 text-base border">
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

export function renderStep3() {
    return html`
        <div>
            <h2 class="text-2xl font-bold mb-2">Paso 3: Tu Catálogo</h2>
            <div class="space-y-6">
                <div>
                    <label class="block text-base font-medium text-gray-700 mb-4">Giro de tu negocio: ${fieldTag(true)}</label>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                        ${this.industries.map(ind => html`
                            <button type="button" @click=${() => {
                                this.updateField('archetype', ind.id);
                                if(ind.id === 'liquor' || ind.id === 'cbd') this.updateField('requireAgeVerification', true);
                            }} class="flex flex-col items-center justify-center p-5 border-2 rounded-2xl transition-all cursor-pointer ${this.formData.archetype === ind.id ? 'border-indigo-500 bg-indigo-50 ring-2 ring-indigo-500 shadow-md transform scale-105' : 'border-gray-200 bg-white'}">
                                <span class="text-4xl mb-3">${ind.icon}</span>
                                <span class="text-sm font-bold text-gray-800 text-center leading-tight">${ind.name}</span>
                            </button>
                        `)}
                    </div>
                </div>

                <div class="bg-red-50 border border-red-200 rounded-xl p-4 mt-4 ${this.formData.requireAgeVerification ? 'ring-2 ring-red-400' : ''}">
                    <div class="flex items-start">
                        <input type="checkbox" .checked=${this.formData.requireAgeVerification} @change=${e => this.updateField('requireAgeVerification', e.target.checked)} class="mt-1 h-5 w-5 text-red-600 rounded">
                        <div class="ml-3 text-sm">
                            <label class="font-bold text-red-900 cursor-pointer">Vende productos para mayores de 18 años</label>
                            <p class="text-red-700 mt-1 font-medium">⚠️ Por regulación, se pedirá foto de la cédula.</p>
                        </div>
                    </div>
                </div>

                <div class="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-5">
                    <h3 class="text-lg font-bold text-blue-900 mb-2">Tu Catálogo de Productos</h3>
                    <div class="flex items-center justify-between border-t border-blue-200 pt-4 mt-2">
                        <span class="text-sm font-medium text-blue-900">¿Ya tienes tu propia lista de precios?</span>
                        <div class="flex items-center gap-2">
                            <div class="relative group">
                                <span class="text-blue-400 cursor-help text-lg">ⓘ</span>
                                <div class="absolute bottom-full right-0 mb-2 w-64 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                                    <p class="font-bold mb-1">Formatos recomendados:</p>
                                    <ul class="list-disc pl-4 space-y-1">
                                        <li>PDF con texto seleccionable (no imágenes escaneadas)</li>
                                        <li>Excel / CSV con columnas: Producto, Precio</li>
                                        <li>Imagen clara y legible</li>
                                    </ul>
                                    <p class="mt-2 text-gray-300">Máximo 25 MB. Si tu PDF es escaneado, la extracción puede ser imperfecta.</p>
                                </div>
                            </div>
                            <label class="cursor-pointer bg-white border border-blue-300 text-blue-700 px-4 py-2 rounded-lg shadow-sm text-sm font-bold hover:bg-blue-100 ${this.catalogLoading ? 'opacity-50' : ''}">
                                <span>${this.catalogLoading ? 'Procesando...' : 'Subir mi archivo'}</span>
                                <input type="file" accept=".csv,.txt,.pdf,.doc,.xls,.png,.jpg" class="sr-only" @change=${this.handleFileUpload} ?disabled=${this.catalogLoading}>
                            </label>
                        </div>

                        <button @click=${() => { this.showCatalogModal = true; this.loadPresets(); }} class="bg-indigo-600 text-white px-4 py-2 rounded-lg shadow-sm text-sm font-bold hover:bg-indigo-700 transition-colors text-center ml-4">
                            Crear Manualmente
                        </button>
                    </div>

                    ${this.catalogLoading ? html`<div class="text-center p-4 text-blue-600 font-bold">Procesando archivo... Espere un momento.</div>` : ''}
                    ${this.formData.catalogFile ? html`<p class="mt-3 text-green-700 text-sm font-bold bg-green-100 p-2 rounded">✅ Archivo: ${this.catalogFileName}</p>` : ''}
                    ${this.catalogError ? html`<p class="mt-3 text-red-700 text-sm font-bold bg-red-100 p-2 rounded">${this.catalogError}</p>` : ''}

                    ${this.formData.catalogItems.length > 0 ? html`
                        <div class="mt-4 bg-white rounded border border-blue-200 overflow-hidden">
                            <div class="bg-blue-100 px-3 py-2 text-sm font-bold text-blue-900 flex justify-between items-center">
                                <span>Verifica tu menú extraído:</span>
                                <span class="text-xs font-normal">${this.formData.catalogItems.length} items</span>
                            </div>
                            <div class="max-h-48 overflow-y-auto">
                                <table class="w-full text-sm text-left">
                                    <thead class="text-xs text-gray-700 uppercase bg-gray-50 border-b">
                                        <tr>
                                            <th class="px-3 py-2">Producto</th>
                                            <th class="px-3 py-2 w-24">Precio ($)</th>
                                            <th class="px-3 py-2 w-10"></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${this.formData.catalogItems.map((item, index) => html`
                                            <tr class="border-b hover:bg-gray-50 transition-colors">
                                                <td class="px-3 py-2">
                                                    <div class="flex items-center gap-2">
                                                        ${item.image ? html`
                                                            <img src=${item.image} alt="" class="w-8 h-8 rounded object-cover border border-gray-200 flex-shrink-0" title="Imagen cargada">
                                                        ` : html`
                                                            <div class="w-8 h-8 rounded bg-gray-100 flex items-center justify-center flex-shrink-0 text-gray-400 text-xs">📷</div>
                                                        `}
                                                        <input type="text" title="Nombre de tu producto o servicio" .value=${item.name} @input=${e => { item.name = e.target.value; this.requestUpdate(); }} class="w-full bg-transparent border-0 text-sm focus:ring-indigo-500">
                                                    </div>
                                                </td>
                                                <td class="px-3 py-2"><input type="number" step="0.01" title="Precio final al cliente" .value=${item.price} @input=${e => { item.price = e.target.value; this.requestUpdate(); }} class="w-full bg-transparent border-0 text-sm focus:ring-indigo-500"></td>
                                                <td class="px-3 py-2 text-center flex justify-around items-center gap-2">
                                                    <label title=${item.image ? "Cambiar foto del producto" : "Subir foto del producto"} class="cursor-pointer ${item.image ? 'text-green-600 hover:text-green-800' : 'text-blue-500 hover:text-blue-700'}">
                                                        <input type="file" accept="image/*" class="hidden" @change=${e => this.handleItemImageUpload(e, index)}>
                                                        ${item.image ? html`
                                                            <svg class="w-5 h-5 inline-block" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                                                        ` : html`
                                                            <svg class="w-5 h-5 inline-block" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                                                        `}
                                                    </label>
                                                    <button title="Eliminar producto" @click=${() => { this.formData.catalogItems.splice(index, 1); this.requestUpdate(); }} class="text-red-500 hover:text-red-700">✕</button>
                                                </td>
                                            </tr>
                                        `)}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    ` : ''}
                </div>

                <div class="mt-6 bg-yellow-50 border border-yellow-200 rounded-xl p-5">
                    <h3 class="text-lg font-bold text-yellow-900 mb-2">Promociones Activas</h3>
                    <textarea .value=${this.formData.promotions} @input=${e => this.updateField('promotions', e.target.value)} rows="2" class="w-full rounded-lg border-yellow-300 p-3"></textarea>
                </div>

                <div>
                    <label class="block text-base font-medium text-gray-700">Políticas o Reglas Importantes ${fieldTag(false)}</label>
                    <textarea .value=${this.formData.policies} @input=${e => this.updateField('policies', e.target.value)} rows="3" class="mt-1 block w-full rounded-lg border-gray-300 p-3"></textarea>
                </div>
            </div>
        </div>
    `;
}

export function renderStep4() {
    return html`
        <div>
            <h2 class="text-2xl font-bold mb-2">Paso 4: Personalidad</h2>
            <div class="space-y-6">
                <div>
                    <label class="block text-base font-medium text-gray-700">Nombre del Vendedor ${fieldTag(false)}</label>
                    <input type="text" .value=${this.formData.agentName} @input=${e => this.updateField('agentName', e.target.value)} placeholder="Ej: Sofía" class="mt-1 block w-full rounded-lg border-gray-300 p-3 border">
                </div>
                <div>
                    <label class="block text-base font-medium text-gray-700">Idioma ${fieldTag(false)}</label>
                    <select .value=${this.formData.language} @change=${e => this.updateField('language', e.target.value)} class="mt-1 block w-full rounded-lg border-gray-300 p-3 border">
                        <option value="es">Español</option>
                        <option value="en">Inglés</option>
                    </select>
                </div>
                <div>
                    <label class="block text-base font-medium text-gray-700">Tono ${fieldTag(false)}</label>
                    <select .value=${this.formData.tone} @change=${e => this.updateField('tone', e.target.value)} class="mt-1 block w-full rounded-lg border-gray-300 p-3 border">
                        <option value="friendly">Amigable</option>
                        <option value="formal">Formal</option>
                    </select>
                </div>
                <div class="mt-4 bg-gray-50 p-4 rounded-lg border">
                    <div class="flex justify-between mb-4">
                        <span>Usar Emojis</span>
                        <input type="range" .value=${this.formData.emojis} @input=${e => this.updateField('emojis', e.target.value)} min="0" max="2" class="w-24">
                    </div>
                    <div class="flex justify-between mt-4">
                        <span>Hablar como Ecuatoriano 🇪🇨</span>
                        <input type="checkbox" .checked=${this.formData.useSlang} @change=${e => this.updateField('useSlang', e.target.checked)} class="h-6 w-6 text-indigo-600 rounded">
                    </div>
                </div>
            </div>
        </div>
    `;
}

export function renderStep5() {
    const allowedArray = this.formData.allowedNumbers.split(',').map(n => n.trim()).filter(n => n.length > 0);

    return html`
        <div>
            <h2 class="text-2xl font-bold mb-2">Paso 5: Seguridad y Control</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label title="El número telefónico donde tus clientes enviarán los mensajes" class="block text-base font-medium text-gray-700">Número de WhatsApp del Negocio ${fieldTag(true)}</label>
                    <input type="text" title="Ingresa tu número con código de país, ej. +5939..." .value=${this.formData.whatsappNumber} @input=${e => this.updateField('whatsappNumber', e.target.value)} @blur=${e => this.updateField('whatsappNumber', this.formatWhatsAppNumber(e.target.value))} placeholder="+593..." class="mt-1 block w-full rounded-lg border-gray-300 p-3 border focus:ring-indigo-500 focus:border-indigo-500">
                    ${this.formData.whatsappNumber && !/^\+[1-9]\d{7,14}$/.test(this.formData.whatsappNumber) ? html`<p class="text-xs text-red-600 mt-1">Ingresa un número válido con código de país (ej: +593999999999).</p>` : ''}
                </div>
                <div>
                    <label title="Crea una contraseña segura para entrar a tu Panel de Control de Ventas" class="block text-base font-medium text-gray-700">Contraseña de Administrador ${fieldTag(true)}</label>
                    <input type="password" title="Mínimo 8 caracteres" .value=${this.formData.adminPassword} @input=${e => this.updateField('adminPassword', e.target.value)} placeholder="••••••••" class="mt-1 block w-full rounded-lg border-gray-300 p-3 border focus:ring-indigo-500 focus:border-indigo-500">
                </div>
            </div>

            <div class="mt-6 bg-red-50 p-4 rounded-xl border border-red-200">
                <div class="flex justify-between items-center">
                    <div>
                        <span class="font-bold text-red-900 block text-lg">Control de Edad (Para negocios +18) 🔒</span>
                        <span class="text-sm text-red-700">La IA pedirá una foto de la cédula al cliente antes de permitir cualquier venta.</span>
                    </div>
                    <input type="checkbox" .checked=${this.formData.requireAgeVerification} @change=${e => this.updateField('requireAgeVerification', e.target.checked)} class="h-6 w-6 text-red-600 rounded border-red-300 focus:ring-red-500">
                </div>
            </div>

            <div class="mt-4 bg-indigo-50 p-4 rounded-xl border border-indigo-200">
                <div class="flex justify-between items-center mb-4">
                    <div>
                        <span class="font-bold text-indigo-900 block text-lg">Lista Blanca de Clientes (Modo Privado) 🛡️</span>
                        <span class="text-sm text-indigo-700">Restringe tu asistente para que solo responda a números específicos.</span>
                    </div>
                    <input type="checkbox" .checked=${this.formData.restrictAccess} @change=${e => this.updateField('restrictAccess', e.target.checked)} class="h-6 w-6 text-indigo-600 rounded border-indigo-300 focus:ring-indigo-500">
                </div>

                ${this.formData.restrictAccess ? html`
                    <div class="mt-4 pt-4 border-t border-indigo-200">
                        <label class="block text-base font-medium text-indigo-900 mb-2">Agregar número permitido</label>
                        <div class="flex gap-2">
                            <input type="text" id="newNumberInput" placeholder="Ej: +593912345678" class="flex-1 rounded-lg border-indigo-300 p-3 border shadow-sm focus:ring-indigo-500 focus:border-indigo-500" @keydown=${e => {
                                if (e.key === 'Enter') {
                                    e.preventDefault();
                                    const val = e.target.value.trim();
                                    if (val) {
                                        const newArr = [...allowedArray, val];
                                        this.updateField('allowedNumbers', newArr.join(', '));
                                        e.target.value = '';
                                    }
                                }
                            }}>
                            <button type="button" @click=${() => {
                                const input = this.querySelector('#newNumberInput');
                                const val = input.value.trim();
                                if (val) {
                                    const newArr = [...allowedArray, val];
                                    this.updateField('allowedNumbers', newArr.join(', '));
                                    input.value = '';
                                }
                            }} class="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-3 rounded-lg font-bold shadow-sm transition-colors text-xl leading-none">
                                +
                            </button>
                        </div>

                        ${allowedArray.length > 0 ? html`
                            <div class="mt-4 flex flex-wrap gap-2">
                                ${allowedArray.map(num => html`
                                    <span class="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-white border border-indigo-300 text-indigo-800 shadow-sm">
                                        ${num}
                                        <button type="button" @click=${() => {
                                            const newArr = allowedArray.filter(n => n !== num);
                                            this.updateField('allowedNumbers', newArr.join(', '));
                                        }} class="ml-2 inline-flex items-center justify-center w-5 h-5 rounded-full text-indigo-400 hover:bg-indigo-100 hover:text-indigo-600 focus:outline-none">
                                            <span class="text-xs font-bold">✕</span>
                                        </button>
                                    </span>
                                `)}
                            </div>
                        ` : html`
                            <p class="text-sm text-indigo-500 mt-3 italic">No has agregado ningún número. El asistente no responderá a nadie.</p>
                        `}
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

export function renderStep6() {


    return html`
        <div class="text-center">
            <div class="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-indigo-100 mb-4 animate-bounce">
                <span class="text-3xl">🎉</span>
            </div>
            <h2 class="text-3xl font-extrabold mb-3 text-gray-900">¡Casi terminamos!</h2>
            <p class="text-gray-600 mb-8 text-lg">Tu nuevo empleado digital está listo.</p>
            ${this.errorMessage ? html`<p class="text-red-500 font-bold mb-4">${this.errorMessage}</p>` : ''}
        </div>
    `;
}

export function renderStep7() {
    return html`
        <div class="text-center py-10">
            <div class="mx-auto flex items-center justify-center h-24 w-24 rounded-full ${this.qrStatus === 'connected' ? 'bg-green-100' : 'bg-indigo-100'} mb-6">
                <span class="text-5xl">${this.qrStatus === 'connected' ? '✅' : '📱'}</span>
            </div>
            <h2 class="text-3xl font-extrabold mb-4 text-gray-900">
                ${this.qrStatus === 'connected' ? '¡Conectado Exitosamente!' : 'Escanea el Código QR'}
            </h2>

            ${this.qrStatus === 'connected' ? html`
                <p class="text-gray-600 mb-8 text-lg">Tu vendedor de inteligencia artificial está activo y listo para trabajar.</p>
                <a href="/" class="inline-block bg-gray-900 hover:bg-black text-white font-bold py-4 px-8 rounded-xl shadow-lg mt-4">
                    Ir a mi Panel de Control
                </a>
            ` : html`
                <p class="text-gray-600 mb-6 text-lg">Abre WhatsApp en tu teléfono, ve a Dispositivos Vinculados, y escanea este código QR para conectar el cerebro de la IA a tu número.</p>

                <div class="flex justify-center mb-6">
                    ${this.qrDataUrl ? html`
                        <img src="${this.qrDataUrl}" alt="WhatsApp QR Code" class="h-64 w-64 border-4 border-white shadow-lg rounded-lg">
                    ` : html`
                        <div class="animate-pulse flex flex-col items-center">
                            <div class="h-48 w-48 bg-gray-200 rounded-lg mb-4"></div>
                            <p class="text-sm text-gray-500">Generando código seguro...</p>
                        </div>
                    `}
                </div>
                <p class="text-sm text-gray-500 mb-4">Una vez escaneado, la pantalla se actualizará automáticamente.</p>
            `}
        </div>
    `;
}

export function renderNavigation() {
    const validation = this.getStepValidation ? this.getStepValidation(this.step) : { valid: true, missing: [] };
    const canProceed = this.step >= 6 || validation.valid;

    return html`
        <div class="mt-10 flex justify-between pt-6 border-t border-gray-200">
            ${this.step > 1 ? html`
                <button @click=${() => this.step--} class="bg-gray-100 text-gray-800 font-bold py-3 px-6 rounded-lg text-lg">Atrás</button>
            ` : html`<div class="w-20"></div>`}

            ${this.step < 6 ? html`
                <button
                    @click=${this.goToNextStep}
                    ?disabled=${!canProceed}
                    title=${!canProceed ? `Completa los campos requeridos: ${validation.missing.join(', ')}` : ''}
                    class="font-bold py-3 px-8 rounded-lg shadow-md ml-auto text-lg ${canProceed ? 'bg-indigo-600 hover:bg-indigo-700 text-white' : 'bg-indigo-300 text-white cursor-not-allowed'}"
                >Siguiente</button>
            ` : html`
                <button @click=${this.submitSetup} class="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-8 rounded-lg shadow-md ml-auto flex items-center text-lg" ?disabled=${this.loading}>
                    <span>${this.loading ? 'Guardando...' : '🚀 ¡Terminar y Activar!'}</span>
                </button>
            `}
        </div>
        ${this.errorMessage ? html`<p class="mt-3 text-sm font-semibold text-red-600">${this.errorMessage}</p>` : ''}
    `;
}

export function renderCopilot() {
    return html`
        <div class="fixed bottom-6 right-6 z-50">
            ${this.showCopilot ? html`
                <div class="bg-white rounded-xl shadow-2xl border border-indigo-100 p-4 mb-4 w-96 text-sm flex flex-col h-[32rem]">
                    <div class="flex justify-between items-center border-b pb-2 mb-2">
                        <h3 class="font-bold text-indigo-900">✨ Asistente de Configuración</h3>
                        <button @click=${() => this.showCopilot = false} class="text-gray-400">✕</button>
                    </div>
                    <div class="flex-grow overflow-y-auto space-y-3 p-1 flex flex-col" id="chat-container">
                        ${this.chatMessages.map(msg => html`
                            <div class="${msg.role === 'user' ? 'text-right' : 'text-left'}">
                                <span class="${msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-800'} inline-block p-3 rounded-2xl max-w-[90%] whitespace-pre-wrap shadow-sm">${msg.content}</span>
                            </div>
                        `)}
                        ${this.chatLoading ? html`<div class="text-left text-indigo-500 text-xs italic mt-2 mt-auto">✨ Pensando...</div>` : ''}
                    </div>
                    <div class="mt-3 flex gap-2 items-center relative">
                        <label class="cursor-pointer text-gray-400 hover:text-indigo-600">
                            📎
                            <input type="file" class="hidden" accept="audio/*,image/*" @change=${this.handleCopilotFile}>
                        </label>
                        <input type="text" .value=${this.chatInput} @input=${e => this.chatInput = e.target.value} @keyup=${e => e.key === 'Enter' && this.sendChat()} placeholder="Pregúntame..." class="flex-grow rounded-lg border border-gray-300 p-2 text-sm">
                        <button @click=${this.sendChat} class="bg-indigo-600 text-white px-3 py-2 rounded-lg font-bold" ?disabled=${this.chatLoading}>→</button>
                    </div>
                    ${this.chatFile ? html`
                        <div class="text-xs text-indigo-600 truncate mt-1">📎 Adjunto: ${this.chatFileName}
                            <button @click=${() => { this.chatFile = null; this.chatFileName = ''; this.requestUpdate(); }} class="ml-2 text-red-500">✕</button>
                        </div>
                    ` : ''}
                </div>
            ` : ''}
            <button @click=${() => this.showCopilot = !this.showCopilot} class="bg-indigo-600 hover:bg-indigo-700 text-white rounded-full p-4 shadow-lg float-right text-2xl">✨</button>
        </div>
    `;
}

export function renderCatalogModal() {
    const items = this.formData.catalogItems || [];
    return html`
        <div class="fixed inset-0 z-[90] flex items-center justify-center bg-gray-900/60 backdrop-blur-sm" @click=${() => { this.showCatalogModal = false; }}>
            <div class="bg-white/95 rounded-2xl shadow-2xl border border-white/50 w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col" @click=${e => e.stopPropagation()}>
                <div class="p-6 border-b border-gray-200 flex justify-between items-center bg-white rounded-t-2xl">
                    <div>
                        <h3 class="text-xl font-bold text-gray-900">Revisa tu Catálogo</h3>
                        <p class="text-sm text-gray-500 mt-1">Edita, elimina o agrega productos antes de continuar.</p>
                    </div>
                    <button @click=${() => { this.showCatalogModal = false; }} class="text-gray-400 hover:text-gray-600 text-2xl leading-none">✕</button>
                </div>

                <div class="p-6 overflow-y-auto flex-grow">
                    ${items.length === 0 ? html`
                        <div class="text-center text-gray-500 py-8">
                            <p class="text-lg mb-2">No hay productos aún.</p>
                            <p class="text-sm">Usa los campos de abajo para agregar el primero.</p>
                        </div>
                    ` : html`
                        <div class="space-y-3 mb-6">
                            ${items.map((item, index) => html`
                                <div class="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-xl p-3">
                                    <div class="flex-1 min-w-0">
                                        <input type="text" .value=${item.name} @input=${e => { item.name = e.target.value; this.requestUpdate(); }} placeholder="Nombre del producto" class="w-full bg-transparent border-0 font-semibold text-sm focus:ring-0 p-0 mb-1">
                                        <input type="text" .value=${item.description || ''} @input=${e => { item.description = e.target.value; this.requestUpdate(); }} placeholder="Descripción (opcional)" class="w-full bg-transparent border-0 text-xs text-gray-500 focus:ring-0 p-0">
                                    </div>
                                    <div class="w-24">
                                        <input type="number" step="0.01" .value=${item.price} @input=${e => { item.price = e.target.value; this.requestUpdate(); }} placeholder="Precio" class="w-full bg-white border border-gray-300 rounded-lg text-sm p-2 text-right focus:ring-indigo-500 focus:border-indigo-500">
                                    </div>
                                    <button @click=${() => { this.formData.catalogItems.splice(index, 1); this.requestUpdate(); }} class="text-red-500 hover:text-red-700 p-2" title="Eliminar">✕</button>
                                </div>
                            `)}
                        </div>
                    `}

                    <div class="border-t border-gray-200 pt-4">
                        <p class="text-sm font-semibold text-gray-700 mb-3">Agregar nuevo producto</p>
                        <div class="flex items-end gap-2">
                            <div class="flex-1">
                                <input type="text" .value=${this.newItem.name} @input=${e => this.newItem.name = e.target.value} placeholder="Nombre" class="w-full rounded-lg border-gray-300 p-2 text-sm border focus:ring-indigo-500 focus:border-indigo-500 mb-2">
                                <input type="text" .value=${this.newItem.description} @input=${e => this.newItem.description = e.target.value} placeholder="Descripción" class="w-full rounded-lg border-gray-300 p-2 text-sm border focus:ring-indigo-500 focus:border-indigo-500">
                            </div>
                            <div class="w-28">
                                <input type="number" step="0.01" .value=${this.newItem.price} @input=${e => this.newItem.price = e.target.value} placeholder="Precio" class="w-full rounded-lg border-gray-300 p-2 text-sm border focus:ring-indigo-500 focus:border-indigo-500">
                            </div>
                            <button @click=${() => {
                                if (!this.newItem.name || !this.newItem.price) return;
                                this.formData.catalogItems.push({ ...this.newItem });
                                this.newItem = { name: '', description: '', price: '' };
                                this.requestUpdate();
                            }} class="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-bold text-sm shadow-sm transition-colors mb-0">+</button>
                        </div>
                    </div>
                </div>

                <div class="p-6 border-t border-gray-200 bg-gray-50 rounded-b-2xl flex justify-between items-center">
                    <span class="text-sm text-gray-500">${items.length} producto${items.length !== 1 ? 's' : ''}</span>
                    <button @click=${() => { this.showCatalogModal = false; }} class="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-6 rounded-lg shadow-sm transition-colors">
                        ${items.length > 0 ? 'Confirmar y Cerrar' : 'Cerrar'}
                    </button>
                </div>
            </div>
        </div>
    `;
}
