
import { renderSidebar } from './sidebar-render.js';
import { renderDashboard } from './dashboard-render.js';
import { renderPlanWizard } from './plan-wizard-render.js';
import { renderTenantWizard } from './tenant-wizard-render.js';
import { renderTenantRow } from './tenants-table-render.js';
import { renderPodRow } from './pods-table-render.js';
import { renderPlanRow } from './plans-table-render.js';
import { renderVaultRow } from './vault-table-render.js';
import { renderInteractionRow } from './interactions-table-render.js';
import { LitElement, html, css } from '/static/tenants/vendor/lit-core-3.min.js';

        class MasterControlPlane extends LitElement {
            static get properties() {
                return {
                    currentView: { type: String },
                    tenants: { type: Array },
                    pods: { type: Array },
                    plans: { type: Array },
                    vaultRecords: { type: Array },
                    interactions: { type: Array },
                    pendingChallenges: { type: Array },
                    loading: { type: Boolean },
                    deploymentMode: { type: String },
                    
                    showWizard: { type: Boolean },
                    wizardStep: { type: Number },
                    wizardData: { type: Object },
                    wizardLoading: { type: Boolean },
                    wizardError: { type: String },
                    
                    showPlanWizard: { type: Boolean },
                    planWizardMode: { type: String },
                    planWizardData: { type: Object },
                    
                    logsModal: { type: Boolean },
                    logsContent: { type: String },
                    logsTenantName: { type: String },
                    actionLoading: { type: String },
                };
            }

            constructor() {
                super();
                this.currentView = 'dashboard';
                this.tenants = [];
                this.pods = [];
                this.plans = [];
                this.vaultRecords = [];
                this.interactions = [];
                this.pendingChallenges = [];
                this.loading = true;
                
                this.showWizard = false;
                this.wizardStep = 1;
                this.wizardData = {
                    business_name: '',
                    owner_full_name: '',
                    owner_email: '',
                    owner_phone_e164: '',
                    plan_name: 'free'
                };
                this.wizardLoading = false;
                this.wizardError = '';
                this.deploymentMode = 'vultr';
                this.logsModal = false;
                this.logsContent = '';
                this.logsTenantName = '';
                this.actionLoading = '';
                
                // Plan Wizard
                this.showPlanWizard = false;
                this.planWizardMode = 'create';
                this.planWizardData = this.defaultPlanData();
                
                const csrfMeta = document.querySelector('meta[name="csrf-token"]');
                this.csrfToken = csrfMeta ? csrfMeta.content : '';
                this.fetchAllData();
                
                // Start polling for Creator Override challenges
                this.challengePollInterval = setInterval(() => this.fetchPendingChallenges(), 5000);
            }

            disconnectedCallback() {
                super.disconnectedCallback();
                if (this.challengePollInterval) clearInterval(this.challengePollInterval);
            }

            createRenderRoot() { return this; }

            async fetchAllData() {
                this.loading = true;
                try {
                    const [resT, resPods, resP, resV, resI] = await Promise.all([
                        fetch('/api/saas/tenants', { credentials: 'same-origin' }),
                        fetch('/api/saas/pods', { credentials: 'same-origin' }),
                        fetch('/api/saas/plans', { credentials: 'same-origin' }),
                        fetch('/api/saas/vault', { credentials: 'same-origin' }),
                        fetch('/api/saas/interactions', { credentials: 'same-origin' })
                    ]);
                    
                    if(resT.ok) this.tenants = await resT.json();
                    if(resPods.ok) this.pods = await resPods.json();
                    if(resP.ok) this.plans = await resP.json();
                    if(resV.ok) this.vaultRecords = await resV.json();
                    if(resI.ok) this.interactions = await resI.json();
                    
                    await Promise.all([
                        this.fetchPendingChallenges(),
                        this.fetchDeploymentMode()
                    ]);
                } catch (e) {
                    console.error("Fetch error", e);
                }
                this.loading = false;
            }

            async fetchDeploymentMode() {
                try {
                    const res = await fetch('/api/saas/system/deployment-mode', { credentials: 'same-origin' });
                    if (res.ok) {
                        const data = await res.json();
                        this.deploymentMode = data.mode || 'vultr';
                    }
                } catch (e) {
                    console.error("Mode fetch error", e);
                }
            }

            async toggleDeploymentMode() {
                const newMode = this.deploymentMode === 'docker' ? 'vultr' : 'docker';
                try {
                    const res = await fetch('/api/saas/system/deployment-mode', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': this.csrfToken, 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: newMode })
                    });
                    if (res.ok) {
                        this.deploymentMode = newMode;
                    }
                } catch (e) {
                    console.error("Mode toggle error", e);
                }
            }

            async tenantAction(tenantId, action, tenantName) {
                this.actionLoading = `${tenantId}-${action}`;
                try {
                    const res = await fetch(`/api/saas/tenants/${tenantId}/${action}`, {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': this.csrfToken }
                    });
                    const data = await res.json();
                    if (!data.ok && data.message) {
                        alert(data.message);
                    }
                    this.fetchAllData();
                } catch (e) {
                    alert(`Error: ${e.message}`);
                }
                this.actionLoading = '';
            }

            async podAction(podId, action, method = 'POST') {
                this.actionLoading = `${podId}-${action}`;
                try {
                    const url = action ? `/api/saas/pods/${podId}/${action}` : `/api/saas/pods/${podId}`;
                    const res = await fetch(url, {
                        method,
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': this.csrfToken }
                    });
                    const data = await res.json();
                    if (!res.ok && data.message) {
                        alert(data.message);
                    }
                    await this.fetchAllData();
                } catch (e) {
                    alert(`Error: ${e.message}`);
                }
                this.actionLoading = '';
            }

            async reconcilePods() {
                this.actionLoading = 'pods-reconcile';
                try {
                    const res = await fetch('/api/saas/pods/reconcile', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': this.csrfToken }
                    });
                    const data = await res.json();
                    if (!res.ok && data.message) {
                        alert(data.message);
                    }
                    await this.fetchAllData();
                } catch (e) {
                    alert(`Error: ${e.message}`);
                }
                this.actionLoading = '';
            }

            async viewLogs(tenantId, tenantName) {
                this.logsTenantName = tenantName;
                this.logsContent = 'Cargando...';
                this.logsModal = true;
                try {
                    const res = await fetch(`/api/saas/tenants/${tenantId}/container-logs?tail=200`, { credentials: 'same-origin' });
                    if (res.ok) {
                        const data = await res.json();
                        this.logsContent = data.logs || 'Sin logs disponibles.';
                    } else {
                        this.logsContent = 'Error al obtener logs.';
                    }
                } catch (e) {
                    this.logsContent = `Error: ${e.message}`;
                }
            }

            async viewPodLogs(podId, podName) {
                this.logsTenantName = podName;
                this.logsContent = 'Cargando...';
                this.logsModal = true;
                try {
                    const res = await fetch(`/api/saas/pods/${podId}/logs?tail=200`, { credentials: 'same-origin' });
                    if (res.ok) {
                        const data = await res.json();
                        this.logsContent = data.logs || 'Sin logs disponibles.';
                    } else {
                        this.logsContent = 'Error al obtener logs.';
                    }
                } catch (e) {
                    this.logsContent = `Error: ${e.message}`;
                }
            }

            closeLogsModal() {
                this.logsModal = false;
                this.logsContent = '';
            }

            async fetchPendingChallenges() {
                try {
                    const res = await fetch('/api/saas/auth/pending-challenges', { credentials: 'same-origin' });
                    if (res.ok) {
                        this.pendingChallenges = await res.json();
                    }
                } catch (e) {
                    console.error("Poll error", e);
                }
            }

            // Wizard methods...
            openWizard() {
                const firstPlan = this.plans.find(p => p.is_active) || this.plans[0];
                this.wizardData = {
                    business_name: '',
                    owner_full_name: '',
                    owner_email: '',
                    owner_phone_e164: '',
                    plan_name: firstPlan ? (firstPlan.slug || firstPlan.name) : 'free'
                };
                this.wizardStep = 1;
                this.wizardError = '';
                this.showWizard = true;
            }
            closeWizard() { this.showWizard = false; }
            nextStep() {
                if (this.wizardStep === 1 && (!this.wizardData.business_name || !this.wizardData.owner_full_name || !this.wizardData.owner_email || !this.wizardData.owner_phone_e164)) {
                    this.wizardError = "Todos los campos son obligatorios.";
                    return;
                }
                if (this.wizardStep === 1 && !/^\+[1-9]\d{7,14}$/.test(this.wizardData.owner_phone_e164)) {
                    this.wizardError = "El celular debe incluir codigo de pais. Ej: +593979445965.";
                    return;
                }
                this.wizardError = '';
                this.wizardStep++;
            }
            prevStep() { this.wizardStep--; }
            
            async submitWizard() {
                this.wizardLoading = true;
                this.wizardError = '';
                try {
                    const res = await fetch('/api/saas/tenants', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: {
                            'X-CSRFToken': this.csrfToken,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(this.wizardData)
                    });
                    
                    if (res.ok) {
                        this.closeWizard();
                        this.fetchAllData();
                        this.currentView = 'tenants';
                    } else {
                        const err = await res.json();
                        this.wizardError = err.detail || err.message || "Error al crear tenant.";
                    }
                } catch (e) {
                    this.wizardError = "Error de red.";
                }
                this.wizardLoading = false;
            }

            // Plan Wizard methods
            defaultPlanData() {
                return {
                    name: '', slug: '', price_monthly: 0, currency: 'USD',
                    description: '', marketing_badge: '', is_custom_priced: false,
                    trial_days: 0, trial_message_limit: 0, support_level: 'standard',
                    max_conversations: 500, max_numbers: 1, max_messages_per_day: 1000,
                    max_messages_per_minute: 60, max_catalog_items: 500,
                    max_transcription_minutes: 120, max_storage_mb: 1024,
                    max_users: 3, max_agent_contexts: 1,
                    vultr_plan: 'vc2-2c-4gb', a0_image: 'avenderpod:latest',
                    a0_memory_limit: '3g', a0_cpu_limit: '2.0',
                    a0_memory_reservation: '1g', a0_cpu_reservation: '1.0',
                    allow_catalog_upload: true, allow_voice_messages: true,
                    allow_human_handoff: false, allow_creator_override: true,
                    allow_custom_domain: false, allow_integrations: false,
                    allow_mobile_app: false, allow_multichannel: false,
                    allow_outbound_reactivation: false, allow_call_handling: false
                };
            }
            openPlanWizard(mode, plan = null) {
                this.planWizardMode = mode;
                this.planWizardData = plan ? { ...plan } : this.defaultPlanData();
                this.showPlanWizard = true;
                this.wizardError = '';
            }
            closePlanWizard() { this.showPlanWizard = false; }
            
            async submitPlanWizard() {
                this.wizardLoading = true;
                this.wizardError = '';
                const url = this.planWizardMode === 'create' ? '/api/saas/plans' : `/api/saas/plans/${this.planWizardData.id}`;
                const method = this.planWizardMode === 'create' ? 'POST' : 'PUT';
                try {
                    const res = await fetch(url, {
                        method: method,
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': this.csrfToken, 'Content-Type': 'application/json' },
                        body: JSON.stringify(this.planWizardData)
                    });
                    if (res.ok) {
                        this.closePlanWizard();
                        this.fetchAllData();
                    } else {
                        const err = await res.json();
                        this.wizardError = err.detail || err.message || "Error al guardar el plan.";
                    }
                } catch (e) {
                    this.wizardError = "Error de red.";
                }
                this.wizardLoading = false;
            }
            
            async deletePlan(id) {
                if(!confirm('Seguro de eliminar este plan?')) return;
                try {
                    const res = await fetch(`/api/saas/plans/${id}`, {
                        method: 'DELETE',
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': this.csrfToken }
                    });
                    const data = await res.json();
                    if(data.ok) this.fetchAllData();
                    else alert(data.message || data.detail);
                } catch (e) {
                    alert('Error: ' + e);
                }
            }

            // Renders...
            renderSidebar() {
                return renderSidebar.call(this);
            }

            renderDashboard() {
                return renderDashboard.call(this);
            }
            renderTable(title, cols, data, renderRow) {
                return html`
                    <div class="animate-fade-in">
                        <header class="flex justify-between items-center mb-8">
                            <h2 class="text-3xl font-display font-black text-white tracking-tight">${title}</h2>
                            ${title === 'Inquilinos (Tenants)' ? html`
                                <button @click=${this.openWizard} class="btn-primary px-6 py-2.5 rounded-full flex items-center gap-2 text-sm">
                                    Nuevo Tenant
                                </button>
                            ` : title === 'SaaS Plans' ? html`
                                <button @click=${() => this.openPlanWizard('create')} class="btn-primary px-6 py-2.5 rounded-full flex items-center gap-2 text-sm">
                                    Nuevo Plan
                                </button>
                            ` : title === 'Avender Pods' ? html`
                                <button @click=${this.reconcilePods} class="btn-primary px-6 py-2.5 rounded-full flex items-center gap-2 text-sm" ?disabled=${this.actionLoading === 'pods-reconcile'}>
                                    Reconciliar
                                </button>
                            ` : ''}
                        </header>
                        
                        <div class="glass-panel rounded-3xl overflow-hidden">
                            ${this.loading ? html`<div class="p-12 text-center text-slate-400 font-medium">Sincronizando datos...</div>` : html`
                                <table class="w-full text-left border-collapse">
                                    <thead class="bg-white/5 text-slate-400 text-xs uppercase tracking-widest border-b border-white/10">
                                        <tr>${cols.map(c => html`<th class="p-6 font-semibold">${c}</th>`)}</tr>
                                    </thead>
                                    <tbody class="divide-y divide-white/5 text-slate-300">
                                        ${data.length === 0 ? html`<tr><td colspan="${cols.length}" class="p-12 text-center text-slate-500">No hay registros.</td></tr>` : data.map(renderRow)}
                                    </tbody>
                                </table>
                            `}
                        </div>
                    </div>
                `;
            }

            render() {
                return html`
                    <div class="flex min-h-screen">
                        ${this.renderSidebar()}
                        <main class="flex-1 ml-72 p-10 overflow-y-auto h-screen relative z-10">
                            <!-- Premium Background Elements -->
                            <div class="fixed top-0 right-0 w-[800px] h-[600px] bg-brand-pink/10 rounded-full blur-[150px] pointer-events-none transform translate-x-1/3 -translate-y-1/3"></div>
                            <div class="fixed bottom-0 left-1/4 w-[600px] h-[600px] bg-brand-blue/10 rounded-full blur-[150px] pointer-events-none transform -translate-x-1/2 translate-y-1/3"></div>
                            
                            <div class="max-w-7xl mx-auto relative z-10 mt-4">
                                <!-- CREATOR OVERRIDE MONITOR -->
                                ${this.pendingChallenges.length > 0 ? html`
                                    <div class="mb-8 animate-pulse">
                                        ${this.pendingChallenges.map(c => html`
                                            <div class="bg-brand-pink/20 border-2 border-brand-pink/50 rounded-[2rem] p-6 flex items-center justify-between shadow-2xl shadow-brand-pink/20 mb-4">
                                                <div class="flex items-center gap-6">
                                                    <div class="w-16 h-16 rounded-2xl bg-brand-pink flex items-center justify-center shadow-lg shadow-brand-pink/40">
                                                        <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
                                                    </div>
                                                    <div>
                                                        <h4 class="text-xs font-black text-brand-pink uppercase tracking-[0.2em]">Solicitud de Acceso Maestro</h4>
                                                        <p class="text-xl font-display font-black text-white mt-1">Inquilino: ${c.tenant_name}</p>
                                                    </div>
                                                </div>
                                                <div class="text-right">
                                                    <p class="text-[10px] text-slate-400 uppercase font-bold tracking-widest mb-1">Session PIN</p>
                                                    <p class="text-5xl font-display font-black text-brand-pink tracking-[0.1em]">${c.pin}</p>
                                                </div>
                                            </div>
                                        `)}
                                    </div>
                                ` : ''}

                                ${this.currentView === 'dashboard' ? this.renderDashboard() : ''}
                                
                                ${this.currentView === 'tenants' ? this.renderTable('Inquilinos (Tenants)', ['Empresa', 'Backend', 'Estado', 'Puerto', 'Infra ID', 'Acciones'], this.tenants, t => renderTenantRow.call(this, t)) : ''}

                                ${this.currentView === 'pods' ? this.renderTable('Avender Pods', ['Pod', 'Backend', 'Estado DB', 'Health', 'Vault', 'Rate Limits', 'Acciones'], this.pods, p => renderPodRow.call(this, p)) : ''}
                                
                                ${this.currentView === 'plans' ? this.renderTable('SaaS Plans', ['Plan', 'Precio', 'Limites', 'Features', 'Acciones'], this.plans, p => renderPlanRow.call(this, p)) : ''}

                                ${this.currentView === 'vault' ? this.renderTable('Vault Security Logs', ['Fecha', 'Tenant', 'Vault Path'], this.vaultRecords, v => renderVaultRow.call(this, v)) : ''}

                                ${this.currentView === 'interactions' ? this.renderTable('Agent Interactions', ['Fecha', 'Tenant', 'Arquetipo', 'Customer WA', 'Status'], this.interactions, i => renderInteractionRow.call(this, i)) : ''}
                            </div>
                        </main>
                        
                        <!-- LOGS MODAL -->
                        ${this.logsModal ? html`
                            <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#090d14]/90 backdrop-blur-md" @click=${e => { if (e.target === e.currentTarget) this.closeLogsModal(); }}>
                                <div class="glass-panel border-brand-blue/30 rounded-[2rem] w-full max-w-4xl overflow-hidden animate-fade-in flex flex-col shadow-2xl shadow-brand-blue/10" style="max-height: 85vh;">
                                    <div class="p-6 border-b border-white/10 flex justify-between items-center">
                                        <div class="flex items-center gap-3">
                                            <div class="w-10 h-10 rounded-xl bg-brand-blue/20 flex items-center justify-center">
                                                <svg class="w-5 h-5 text-brand-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                                            </div>
                                            <h3 class="text-xl font-display font-black text-white tracking-tight">Logs: <span class="text-brand-blue">${this.logsTenantName}</span></h3>
                                        </div>
                                        <button @click=${this.closeLogsModal} class="text-slate-400 hover:text-white transition"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></button>
                                    </div>
                                    <div class="flex-1 overflow-auto p-6">
                                        <pre class="bg-black/60 rounded-2xl p-6 text-xs text-emerald-400 font-mono leading-relaxed whitespace-pre-wrap overflow-x-auto max-h-[60vh]">${this.logsContent}</pre>
                                    </div>
                                </div>
                            </div>
                        ` : ''}
                        
                        ${renderTenantWizard.call(this)}
                        ${renderPlanWizard.call(this)}
                    </div>
                `;
            }
        }
        customElements.define('saas-control-plane', MasterControlPlane);
