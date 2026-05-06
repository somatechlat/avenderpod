import { html } from 'https://cdn.jsdelivr.net/npm/lit@3.1.2/+esm';
export function renderPlanWizard() {
return this.showPlanWizard ? html`
                            <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#090d14]/90 backdrop-blur-md">
                                <div class="glass-panel border-brand-blue/30 rounded-[2rem] w-full max-w-6xl overflow-hidden animate-fade-in flex flex-col shadow-2xl shadow-brand-blue/10" style="max-height: 90vh;">
                                    <div class="p-6 border-b border-white/10 flex justify-between items-center bg-black/40">
                                        <h3 class="text-2xl font-display font-black text-white tracking-tight">${this.planWizardMode === 'create' ? 'Crear Nuevo Plan' : 'Editar Plan'}</h3>
                                        <button @click=${this.closePlanWizard} class="text-slate-400 hover:text-white transition"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>
                                    </div>
                                    
                                    <div class="flex-1 overflow-auto p-8">
                                        ${this.wizardError ? html`<div class="mb-6 p-4 bg-brand-pink/10 text-brand-pink border border-brand-pink/20 rounded-xl text-sm font-medium">${this.wizardError}</div>` : ''}
                                        
                                        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                                            <!-- Col 1: Información Básica y Limites Comerciales -->
                                            <div class="space-y-6">
                                                <h4 class="text-lg font-black text-brand-blue uppercase tracking-widest border-b border-brand-blue/20 pb-2">Comercial & Limites</h4>
                                                
                                                <div>
                                                    <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Nombre del Plan</label>
                                                    <input type="text" .value=${this.planWizardData.name} @input=${e=>this.planWizardData.name=e.target.value} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-brand-blue focus:ring-1 focus:ring-brand-blue outline-none">
                                                </div>
                                                <div>
                                                    <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Precio Mensual (USD)</label>
                                                    <input type="number" step="0.01" .value=${this.planWizardData.price_monthly} @input=${e=>this.planWizardData.price_monthly=parseFloat(e.target.value)} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-brand-blue focus:ring-1 focus:ring-brand-blue outline-none">
                                                </div>
                                                
                                                <div class="grid grid-cols-2 gap-4">
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Max Conversaciones</label>
                                                        <input type="number" .value=${this.planWizardData.max_conversations} @input=${e=>this.planWizardData.max_conversations=parseInt(e.target.value)} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-brand-blue outline-none">
                                                    </div>
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Max Números WA</label>
                                                        <input type="number" .value=${this.planWizardData.max_numbers} @input=${e=>this.planWizardData.max_numbers=parseInt(e.target.value)} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-brand-blue outline-none">
                                                    </div>
                                                </div>
                                                <div class="grid grid-cols-2 gap-4">
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Mensajes / Día</label>
                                                        <input type="number" .value=${this.planWizardData.max_messages_per_day} @input=${e=>this.planWizardData.max_messages_per_day=parseInt(e.target.value)} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-brand-blue outline-none">
                                                    </div>
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Msg / Minuto (Rate)</label>
                                                        <input type="number" .value=${this.planWizardData.max_messages_per_minute} @input=${e=>this.planWizardData.max_messages_per_minute=parseInt(e.target.value)} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-brand-blue outline-none">
                                                    </div>
                                                </div>
                                                <div class="grid grid-cols-2 gap-4">
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Max Items Catálogo</label>
                                                        <input type="number" .value=${this.planWizardData.max_catalog_items} @input=${e=>this.planWizardData.max_catalog_items=parseInt(e.target.value)} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-brand-blue outline-none">
                                                    </div>
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Minutos Transcripción</label>
                                                        <input type="number" .value=${this.planWizardData.max_transcription_minutes} @input=${e=>this.planWizardData.max_transcription_minutes=parseInt(e.target.value)} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-brand-blue outline-none">
                                                    </div>
                                                </div>
                                            </div>
                                            
                                            <!-- Col 2: Infraestructura (Hardware) -->
                                            <div class="space-y-6">
                                                <h4 class="text-lg font-black text-emerald-400 uppercase tracking-widest border-b border-emerald-400/20 pb-2">Infraestructura & Hardware</h4>
                                                
                                                <div>
                                                    <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Vultr VM Plan (Cloud)</label>
                                                    <input type="text" .value=${this.planWizardData.vultr_plan} @input=${e=>this.planWizardData.vultr_plan=e.target.value} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 outline-none font-mono text-sm">
                                                    <p class="text-[10px] text-slate-500 mt-1">Ej: vc2-2c-4gb, vc2-1c-2gb</p>
                                                </div>
                                                <div>
                                                    <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Docker Image</label>
                                                    <input type="text" .value=${this.planWizardData.a0_image} @input=${e=>this.planWizardData.a0_image=e.target.value} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-emerald-400 focus:ring-1 focus:ring-emerald-400 outline-none font-mono text-sm">
                                                </div>
                                                
                                                <div class="grid grid-cols-2 gap-4">
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Memoria (Limit)</label>
                                                        <input type="text" .value=${this.planWizardData.a0_memory_limit} @input=${e=>this.planWizardData.a0_memory_limit=e.target.value} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-emerald-400 outline-none font-mono text-sm">
                                                    </div>
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">Memoria (Reservation)</label>
                                                        <input type="text" .value=${this.planWizardData.a0_memory_reservation} @input=${e=>this.planWizardData.a0_memory_reservation=e.target.value} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-emerald-400 outline-none font-mono text-sm">
                                                    </div>
                                                </div>
                                                <div class="grid grid-cols-2 gap-4">
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">CPU (Limit)</label>
                                                        <input type="text" .value=${this.planWizardData.a0_cpu_limit} @input=${e=>this.planWizardData.a0_cpu_limit=e.target.value} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-emerald-400 outline-none font-mono text-sm">
                                                    </div>
                                                    <div>
                                                        <label class="block text-xs font-bold text-slate-400 mb-1 uppercase">CPU (Reservation)</label>
                                                        <input type="text" .value=${this.planWizardData.a0_cpu_reservation} @input=${e=>this.planWizardData.a0_cpu_reservation=e.target.value} class="w-full bg-black/40 border border-white/10 text-white rounded-xl px-4 py-2 focus:border-emerald-400 outline-none font-mono text-sm">
                                                    </div>
                                                </div>
                                            </div>
                                            
                                            <!-- Col 3: Feature Gates -->
                                            <div class="space-y-6">
                                                <h4 class="text-lg font-black text-brand-pink uppercase tracking-widest border-b border-brand-pink/20 pb-2">Feature Gates</h4>
                                                
                                                <div class="grid gap-3">
                                                    ${[
                                                        {key: 'allow_catalog_upload', label: 'Catálogo de Productos'},
                                                        {key: 'allow_voice_messages', label: 'Mensajes de Voz (STT)'},
                                                        {key: 'allow_human_handoff', label: 'Desvío a Humano'},
                                                        {key: 'allow_creator_override', label: 'God Mode (Creator)'},
                                                        {key: 'allow_custom_domain', label: 'Dominio Personalizado'},
                                                        {key: 'allow_integrations', label: 'APIs e Integraciones Externas'},
                                                        {key: 'allow_mobile_app', label: 'Acceso App Móvil'},
                                                        {key: 'allow_multichannel', label: 'Multicanal (IG, FB)'},
                                                        {key: 'allow_outbound_reactivation', label: 'Campañas Outbound'},
                                                        {key: 'allow_call_handling', label: 'Recepción de Llamadas'}
                                                    ].map(f => html`
                                                        <label class="flex items-center gap-3 cursor-pointer p-2 rounded-lg hover:bg-white/5 transition">
                                                            <input type="checkbox" ?checked=${this.planWizardData[f.key]} @change=${e => this.planWizardData[f.key] = e.target.checked} class="w-4 h-4 rounded bg-black/50 border-white/20 text-brand-pink focus:ring-brand-pink focus:ring-offset-0">
                                                            <span class="text-sm font-medium text-slate-300">${f.label}</span>
                                                        </label>
                                                    `)}
                                                </div>
                                                
                                                <label class="flex items-center gap-3 cursor-pointer p-4 rounded-xl bg-brand-cyan/10 border border-brand-cyan/20 mt-4">
                                                    <input type="checkbox" ?checked=${this.planWizardData.is_active} @change=${e => this.planWizardData.is_active = e.target.checked} class="w-5 h-5 rounded bg-black/50 border-brand-cyan text-brand-cyan focus:ring-brand-cyan focus:ring-offset-0">
                                                    <span class="font-bold text-brand-cyan">Plan Activo (Visible para Asignación)</span>
                                                </label>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div class="p-6 border-t border-white/10 flex justify-end gap-4 bg-black/40">
                                        <button @click=${this.closePlanWizard} class="px-6 py-2.5 text-slate-400 hover:text-white font-bold transition">Cancelar</button>
                                        <button @click=${this.submitPlanWizard} ?disabled=${this.wizardLoading} class="btn-gradient px-8 py-2.5 rounded-xl flex items-center gap-2 disabled:opacity-50">
                                            ${this.wizardLoading ? html`Guardando...` : 'Guardar Plan'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ` : '';
}
