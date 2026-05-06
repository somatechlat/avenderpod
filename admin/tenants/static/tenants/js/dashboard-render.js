import { html } from 'https://cdn.jsdelivr.net/npm/lit@3.1.2/+esm';
export function renderDashboard() {
    return html`
                    <div class="animate-fade-in space-y-8">
                        <header class="flex justify-between items-end">
                            <div>
                                <h2 class="text-4xl font-display font-black text-white tracking-tight mb-2">System Administration<br><span class="text-gradient">Control Plane</span></h2>
                                <p class="text-slate-400 max-w-xl text-lg leading-relaxed">Global Infrastructure Metrics and Multi-Tenant SaaS provisioning.</p>
                            </div>
                            <button @click=${this.openWizard} class="btn-primary px-8 py-3.5 rounded-full flex items-center gap-2 text-sm">
                                Nuevo Tenant <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                            </button>
                        </header>
                        
                        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                            <div class="glass-panel p-8 rounded-3xl relative overflow-hidden group">
                                <div class="absolute -right-6 -top-6 w-32 h-32 bg-brand-pink/20 rounded-full blur-3xl group-hover:bg-brand-pink/30 transition duration-500"></div>
                                <h3 class="text-slate-400 text-sm font-semibold tracking-wide uppercase">Total Tenants</h3>
                                <p class="text-5xl font-display font-black text-white mt-4 tracking-tight">${this.tenants.length}</p>
                            </div>
                            <div class="glass-panel p-8 rounded-3xl relative overflow-hidden group">
                                <div class="absolute -right-6 -top-6 w-32 h-32 bg-brand-blue/20 rounded-full blur-3xl group-hover:bg-brand-blue/30 transition duration-500"></div>
                                <h3 class="text-slate-400 text-sm font-semibold tracking-wide uppercase">Planes Activos</h3>
                                <p class="text-5xl font-display font-black text-white mt-4 tracking-tight">${this.plans.length}</p>
                            </div>
                            <div class="glass-panel p-8 rounded-3xl relative overflow-hidden group">
                                <div class="absolute -right-6 -top-6 w-32 h-32 bg-brand-cyan/20 rounded-full blur-3xl group-hover:bg-brand-cyan/30 transition duration-500"></div>
                                <h3 class="text-slate-400 text-sm font-semibold tracking-wide uppercase">Interacciones</h3>
                                <p class="text-5xl font-display font-black text-white mt-4 tracking-tight">${this.interactions.length}</p>
                            </div>
                            <div class="glass-panel p-8 rounded-3xl relative overflow-hidden group">
                                <div class="absolute -right-6 -top-6 w-32 h-32 bg-indigo-500/20 rounded-full blur-3xl group-hover:bg-indigo-500/30 transition duration-500"></div>
                                <h3 class="text-slate-400 text-sm font-semibold tracking-wide uppercase">Vault Logs</h3>
                                <p class="text-5xl font-display font-black text-white mt-4 tracking-tight">${this.vaultRecords.length}</p>
                            </div>
                        </div>
                    </div>
                `;
}
