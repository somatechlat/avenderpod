import { html } from 'https://cdn.jsdelivr.net/npm/lit@3.1.2/+esm';
export function renderTenantWizard() {
return this.showWizard ? html`
                            <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#090d14]/90 backdrop-blur-md">
                                <div class="glass-panel border-brand-pink/30 rounded-[2rem] w-full max-w-2xl overflow-hidden animate-fade-in flex flex-col shadow-2xl shadow-brand-pink/10">
                                    <div class="p-8 border-b border-white/10 flex justify-between items-center">
                                        <h3 class="text-2xl font-display font-black text-white tracking-tight">Nuevo Inquilino <span class="text-brand-pink text-lg ml-2 font-medium">Paso ${this.wizardStep} de 3</span></h3>
                                        <button @click=${this.closeWizard} class="text-slate-400 hover:text-white transition"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>
                                    </div>
                                    
                                    <div class="p-10">
                                        ${this.wizardError ? html`<div class="mb-6 p-4 bg-brand-pink/10 text-brand-pink border border-brand-pink/20 rounded-xl text-sm font-medium">${this.wizardError}</div>` : ''}
                                        
                                        ${this.wizardStep === 1 ? html`
                                            <div class="space-y-6">
                                                <div>
                                                    <label class="block text-sm font-bold text-slate-400 mb-2 uppercase tracking-wider">Nombre de la Empresa</label>
                                                    <input type="text" .value=${this.wizardData.business_name} @input=${e=>this.wizardData.business_name=e.target.value} placeholder="Ej: Zapateria El Sol" class="w-full bg-black/40 border border-white/10 text-white rounded-2xl px-5 py-4 focus:outline-none focus:border-brand-pink focus:ring-1 focus:ring-brand-pink transition">
                                                </div>
                                                <div>
                                                    <label class="block text-sm font-bold text-slate-400 mb-2 uppercase tracking-wider">Nombre del Dueño</label>
                                                    <input type="text" .value=${this.wizardData.owner_full_name} @input=${e=>this.wizardData.owner_full_name=e.target.value} placeholder="Ej: Maria Perez" class="w-full bg-black/40 border border-white/10 text-white rounded-2xl px-5 py-4 focus:outline-none focus:border-brand-pink focus:ring-1 focus:ring-brand-pink transition">
                                                </div>
                                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                    <div>
                                                        <label class="block text-sm font-bold text-slate-400 mb-2 uppercase tracking-wider">Correo Electrónico</label>
                                                        <input type="email" .value=${this.wizardData.owner_email} @input=${e=>this.wizardData.owner_email=e.target.value} placeholder="admin@empresa.com" class="w-full bg-black/40 border border-white/10 text-white rounded-2xl px-5 py-4 focus:outline-none focus:border-brand-pink focus:ring-1 focus:ring-brand-pink transition">
                                                    </div>
                                                    <div>
                                                        <label class="block text-sm font-bold text-slate-400 mb-2 uppercase tracking-wider">Celular WhatsApp</label>
                                                        <input type="tel" .value=${this.wizardData.owner_phone_e164} @input=${e=>this.wizardData.owner_phone_e164=e.target.value} placeholder="+593979445965" class="w-full bg-black/40 border border-white/10 text-white rounded-2xl px-5 py-4 focus:outline-none focus:border-brand-pink focus:ring-1 focus:ring-brand-pink transition">
                                                    </div>
                                                </div>
                                            </div>
                                        ` : ''}
                                        
                                        ${this.wizardStep === 2 ? html`
                                            <div class="space-y-4">
                                                <label class="block text-sm font-bold text-slate-400 mb-4 uppercase tracking-wider">Selecciona un Plan SaaS</label>
                                                <div class="grid gap-4">
                                                    ${this.plans.filter(p => p.is_active).map(p => html`
                                                        <div @click=${() => this.wizardData.plan_name = p.slug || p.name} class="cursor-pointer border-2 rounded-2xl p-6 transition duration-300 ${this.wizardData.plan_name === (p.slug || p.name) ? 'border-brand-pink bg-brand-pink/5' : 'border-white/10 hover:border-white/20 bg-black/20'}">
                                                            <div class="flex justify-between items-center">
                                                                <div>
                                                                    <span class="block font-black text-white text-xl">${p.name} ${p.marketing_badge ? html`<span class="text-xs text-brand-pink ml-2">${p.marketing_badge}</span>` : ''}</span>
                                                                    <span class="block text-sm text-slate-400 mt-1">${p.max_conversations} conversaciones/mes · ${p.max_messages_per_day} mensajes/dia</span>
                                                                </div>
                                                                <span class="font-display font-black text-3xl text-gradient">${p.is_custom_priced ? 'A medida' : `$${p.price_monthly}`}</span>
                                                            </div>
                                                        </div>
                                                    `)}
                                                </div>
                                            </div>
                                        ` : ''}
                                        
                                        ${this.wizardStep === 3 ? html`
                                            <div class="text-center py-8">
                                                <div class="w-24 h-24 rounded-full bg-gradient-brand flex items-center justify-center mx-auto mb-6 shadow-xl shadow-brand-pink/30">
                                                    <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
                                                </div>
                                                <h4 class="text-2xl font-display font-black text-white mb-2">Todo Listo</h4>
                                                <p class="text-slate-400 text-lg">Se provisionara la infraestructura para <strong class="text-white">${this.wizardData.business_name}</strong> bajo el plan <strong class="text-white">${this.wizardData.plan_name}</strong>.</p>
                                            </div>
                                        ` : ''}
                                    </div>
                                    
                                    <div class="p-8 border-t border-white/10 flex justify-between bg-black/20 items-center">
                                        ${this.wizardStep > 1 ? html`<button @click=${this.prevStep} class="px-6 py-3 text-slate-400 hover:text-white font-bold transition">Volver Atrás</button>` : html`<div></div>`}
                                        ${this.wizardStep < 3 ? html`<button @click=${this.nextStep} class="btn-primary px-8 py-3 rounded-full">Continuar</button>` : 
                                            html`<button @click=${this.submitWizard} ?disabled=${this.wizardLoading} class="btn-gradient px-8 py-3 rounded-full flex items-center gap-2 disabled:opacity-50">${this.wizardLoading ? html`<svg class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Procesando...` : 'Lanzar Pod'}</button>`}
                                    </div>
                                </div>
                            </div>
                        ` : '';
}
