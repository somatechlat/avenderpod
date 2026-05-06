import { LitElement, html } from 'https://cdn.jsdelivr.net/gh/lit/dist@3/core/lit-core.min.js';
import * as actions from './onboarding_actions.js';
import * as views from './onboarding_views.js';

export class AvenderWizard extends LitElement {
    static properties = {
        step: { type: Number },
        loading: { type: Boolean },
        errorMessage: { type: String },
        successMessage: { type: String },
        showMap: { type: Boolean },
        showCopilot: { type: Boolean },
        chatMessages: { type: Array },
        chatInput: { type: String },
        chatLoading: { type: Boolean },
        chatFile: { type: Object },
        chatFileName: { type: String },
        formData: { type: Object },
        catalogLoading: { type: Boolean },
        catalogError: { type: String },
        catalogFileName: { type: String },
        industries: { type: Array },
        showCatalogModal: { type: Boolean },
        newItem: { type: Object },
        loadingMessage: { type: String },
        qrStatus: { type: String },
        qrDataUrl: { type: String },
        qrPollTimer: { type: Object },
        toastMessage: { type: String },
        toastType: { type: String },
        toastVisible: { type: Boolean },
    };

    constructor() {
        super();
        this.loading = false;
        this.errorMessage = '';
        this.successMessage = '';
        this.showMap = false;
        this.mapInstance = null;
        this.mapMarker = null;
        this.showCopilot = false;
        this.chatMessages = [{role: 'assistant', content: '¡Hola! Soy tu Copiloto de IA. Pregúntame lo que necesites o envíame un audio/foto.'}];
        this.chatInput = '';
        this.chatLoading = false;
        this.chatFile = null;
        this.chatFileName = '';
        this.showCatalogModal = false;
        this.newItem = { name: '', description: '', price: '' };
        this.toastMessage = '';
        this.toastType = 'success';
        this.toastVisible = false;

        this.formData = {
            idType: 'RUC',
            idNumber: '',
            legalName: '',
            tradeName: '',
            headquarters: '',
            useCustomHours: false,
            hours: 'Lunes a Viernes 09:00 - 18:00',
            deliveryRules: '',
            payTransfer: false,
            payCash: false,
            payLink: false,
            paymentUrl: '',
            archetype: '',
            policies: '',
            agentName: '',
            language: 'es',
            tone: 'friendly',
            useSlang: false,
            emojis: 1,
            whatsappNumber: '',
            adminPassword: '',
            restrictAccess: false,
            allowedNumbers: '',
            catalogFile: null,
            catalogItems: [],
            requireAgeVerification: false,
            promotions: ''
        };

        // Restore form data from localStorage (crash recovery)
        try {
            const saved = localStorage.getItem('avender_wizard_data');
            if (saved) {
                const parsed = JSON.parse(saved);
                // Merge saved data into formData (preserving defaults for missing keys)
                for (const key of Object.keys(this.formData)) {
                    if (parsed[key] !== undefined && parsed[key] !== null) {
                        // Don't restore binary data placeholders
                        if (key === 'catalogFile' && parsed[key]?.content === '[stored]') continue;
                        this.formData[key] = parsed[key];
                    }
                }
                // Restore catalog items but strip placeholder image data
                if (parsed.catalogItems && Array.isArray(parsed.catalogItems)) {
                    this.formData.catalogItems = parsed.catalogItems.map(item => {
                        const copy = { ...item };
                        if (copy.image === '[stored]') delete copy.image;
                        return copy;
                    });
                }
            }
            const savedStep = localStorage.getItem('avender_wizard_step');
            if (savedStep) {
                const parsedStep = parseInt(savedStep, 10);
                // Only restore to steps 1-6 (never auto-resume to 7/QR)
                if (parsedStep >= 1 && parsedStep <= 6) {
                    this.step = parsedStep;
                } else {
                    this.step = 1;
                }
            } else {
                this.step = 1;
            }
        } catch (e) {
            this.step = 1;
        }

        this.catalogLoading = false;
        this.catalogError = '';
        this.catalogFileName = '';
        this.industries = [
            { id: 'restaurant', name: 'Restaurante / Comidas', icon: '🍔' },
            { id: 'retail', name: 'Ropa y Accesorios', icon: '👕' },
            { id: 'groceries', name: 'Minimarket / Abastos', icon: '🛒' },
            { id: 'beauty', name: 'Peluquería / Spa', icon: '✂️' },
            { id: 'tech', name: 'Celulares y Tecnología', icon: '📱' },
            { id: 'services', name: 'Servicios Profesionales', icon: '🔧' },
            { id: 'doctor', name: 'Consultorio Médico', icon: '🩺' },
            { id: 'pharmacy', name: 'Farmacia', icon: '💊' },
            { id: 'hardware', name: 'Ferretería', icon: '🔨' },
            { id: 'liquor', name: 'Licorería', icon: '🍷' },
            { id: 'cbd', name: 'Cannabis / CBD', icon: '🌿' },
            { id: 'other', name: 'Otro Negocio', icon: '📦' }
        ];
        const params = new URLSearchParams(window.location.search);
        this.setupToken = params.get('setup_token') || params.get('token') || localStorage.getItem('avender_setup_token') || '';
        if (this.setupToken) {
            localStorage.setItem('avender_setup_token', this.setupToken);
        }
    }

    createRenderRoot() {
        return this; // Disable shadow DOM for Tailwind CSS
    }

    updated(changedProperties) {
        if (changedProperties.has('showMap') && this.showMap) {
            setTimeout(() => this.initMap(), 100);
        }
    }

    render() {
        return html`
            ${this.renderToast ? this.renderToast() : ''}
            <div class="relative w-full max-w-3xl mx-auto">
                ${this.catalogLoading ? html`
                    <div class="fixed inset-0 z-[100] flex items-center justify-center bg-gray-900 bg-opacity-75 backdrop-blur-sm">
                        <div class="bg-white rounded-2xl shadow-2xl p-8 flex flex-col items-center max-w-md w-full mx-4 text-center border-4 border-indigo-500">
                            <div class="animate-spin rounded-full h-20 w-20 border-t-4 border-b-4 border-indigo-600 mb-6"></div>
                            <h3 class="text-2xl font-black text-indigo-700 mb-3">${this.loadingMessage || 'Cargando...'}</h3>
                            <p class="text-gray-600 text-lg">Por favor, no cierres esta ventana. El agente está procesando tu archivo.</p>
                        </div>
                    </div>
                ` : ''}
                <div class="bg-white rounded-3xl shadow-xl shadow-slate-200/50 border border-slate-100 w-full p-6 md:p-10 overflow-hidden relative z-10">
                ${this.renderHeader()}
                ${this.renderProgressBar()}

                ${this.step === 1 ? this.renderStep1() : ''}
                ${this.step === 2 ? this.renderStep2() : ''}
                ${this.step === 3 ? this.renderStep3() : ''}
                ${this.step === 4 ? this.renderStep4() : ''}
                ${this.step === 5 ? this.renderStep5() : ''}
                ${this.step === 6 ? this.renderStep6() : ''}
                ${this.step === 7 ? this.renderStep7() : ''}

                ${this.step < 7 ? this.renderNavigation() : ''}
                </div>
            </div>

            ${this.showCatalogModal ? this.renderCatalogModal() : ''}
            ${this.renderCopilot()}
        `;
    }

    async connectedCallback() {
        super.connectedCallback();
        // Check if onboarding is already complete and redirect
        try {
            const res = await fetch('/api/plugins/avender/onboarding_api', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({}) });
            const data = await res.json();
            if (!data.ok && data.error && data.error.includes('already completed')) {
                window.location.href = './admin.html';
            }
        } catch (e) { /* ignore */ }
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        if (this.qrPollTimer) clearInterval(this.qrPollTimer);
        if (this.loaderInterval) clearInterval(this.loaderInterval);
        if (this._statusPollTimer) clearTimeout(this._statusPollTimer);
        if (this.mapInstance) {
            this.mapInstance.remove();
            this.mapInstance = null;
        }
    }
}

Object.assign(AvenderWizard.prototype, actions, views);
customElements.define('avender-wizard', AvenderWizard);
