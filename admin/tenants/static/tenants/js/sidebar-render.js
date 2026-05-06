import { html } from 'https://cdn.jsdelivr.net/npm/lit@3.1.2/+esm';
export function renderSidebar() {
    const navBtn = (view, icon, text) => html`
                    <button @click=${() => { this.currentView = view; this.fetchAllData(); }} class="w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition ${this.currentView === view ? 'bg-brand-pink/10 text-brand-pink border border-brand-pink/20' : 'text-slate-400 hover:text-white hover:bg-white/5'}">
                        ${icon} <span class="font-medium tracking-wide text-sm">${text}</span>
                    </button>
                `;
    return html`
                    <aside class="w-72 bg-brand-bg/95 backdrop-blur-xl border-r border-white/5 h-screen flex flex-col fixed top-0 left-0 z-20">
                        <div class="p-8 flex items-center gap-3">
                            <div class="w-8 h-8 rounded-lg bg-gradient-brand flex items-center justify-center">
                                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z"></path></svg>
                            </div>
                            <h1 class="font-display font-black text-2xl tracking-tight text-white italic">¡A VENDER!</h1>
                        </div>
                        
                        <div class="px-6 pb-4">
                            <p class="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3 pl-2">Control Plane</p>
                            <nav class="space-y-1">
                                ${navBtn('dashboard', html`<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"></path></svg>`, 'Dashboard')}
                                ${navBtn('tenants', html`<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>`, 'Inquilinos (Tenants)')}
                                ${navBtn('plans', html`<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`, 'SaaS Plans')}
                            </nav>
                        </div>
                        
                        <div class="px-6 py-4 mt-auto">
                            <p class="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3 pl-2">System Logs</p>
                            <nav class="space-y-1">
                                ${navBtn('vault', html`<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>`, 'Vault Security')}
                                ${navBtn('interactions', html`<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>`, 'Interactions')}
                            </nav>
                        </div>

                        <!-- DEV / PROD Mode Toggle -->
                        <div class="px-6 pb-6">
                            <div class="glass-panel rounded-2xl p-4">
                                <p class="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">Deploy Mode</p>
                                <button @click=${this.toggleDeploymentMode} class="w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-xl transition ${this.deploymentMode === 'docker' ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-violet-500/10 border border-violet-500/30'}">
                                    <span class="flex items-center gap-2">
                                        ${this.deploymentMode === 'docker' ? html`
                                            <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                                            <span class="text-sm font-bold text-emerald-400">🐳 DEV</span>
                                        ` : html`
                                            <span class="w-2.5 h-2.5 rounded-full bg-violet-400"></span>
                                            <span class="text-sm font-bold text-violet-400">☁️ PROD</span>
                                        `}
                                    </span>
                                    <span class="text-[10px] text-slate-500 font-mono">${this.deploymentMode === 'docker' ? 'Docker Local' : 'Vultr Cloud'}</span>
                                </button>
                            </div>
                        </div>
                    </aside>
                `;
}
