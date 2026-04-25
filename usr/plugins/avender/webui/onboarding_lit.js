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
        newItem: { type: Object }
    };

    constructor() {
        super();
        this.step = 1;
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
            archetype: 'restaurant',
            policies: '',
            agentName: '',
            language: 'es',
            tone: 'friendly',
            useSlang: false,
            emojis: 1,
            whatsappNumber: '',
            adminPassword: '',
            restrictAccess: false,
            enableWhitelist: false,
            allowedNumbers: '',
            catalogFile: null,
            catalogItems: [],
            requireAgeVerification: false,
            promotions: ''
        };
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

            ${this.renderCopilot()}
        `;
    }

    disconnectedCallback() {
        super.disconnectedCallback();
        if (this.qrPollTimer) clearInterval(this.qrPollTimer);
    }
}

Object.assign(AvenderWizard.prototype, actions, views);
customElements.define('avender-wizard', AvenderWizard);
