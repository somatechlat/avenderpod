import { html } from '/static/tenants/vendor/lit-core-3.min.js';

/**
 * Render a single tenant row for the Inquilinos (Tenants) table.
 * Called with `this` bound to the MasterControlPlane instance.
 *
 * @param {object} t - Tenant object from the API.
 * @returns {import('lit').TemplateResult}
 */
export function renderTenantRow(t) {
    return html`
        <tr class="hover:bg-white/5 transition duration-200">
            <td class="p-6 font-bold text-white flex items-center gap-4">
                <div class="w-10 h-10 rounded-xl bg-gradient-brand flex items-center justify-center font-black text-white shadow-lg shadow-brand-pink/20">
                    ${t.name.charAt(0).toUpperCase()}
                </div>
                <div>
                    <span>${t.name}</span>
                    <p class="text-xs text-slate-500 font-normal">${t.email}</p>
                </div>
            </td>
            <td class="p-6">
                ${t.deployment_backend === 'docker' ? html`
                    <span class="px-2.5 py-1 text-[10px] font-bold rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">🐳 DOCKER</span>
                ` : html`
                    <span class="px-2.5 py-1 text-[10px] font-bold rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20">☁️ VULTR</span>
                `}
            </td>
            <td class="p-6"><span class="px-3 py-1.5 text-xs font-bold rounded-full border ${t.status === 'active' ? 'bg-brand-cyan/10 text-brand-cyan border-brand-cyan/20' : t.status === 'suspended' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-brand-pink/10 text-brand-pink border-brand-pink/20'}">${t.status.toUpperCase()}</span></td>
            <td class="p-6 font-mono text-slate-500">${t.assigned_port || '-'}</td>
            <td class="p-6 font-mono text-[10px] text-slate-500 break-all w-32">${t.deployment_backend === 'docker' ? (t.docker_container_id ? t.docker_container_id.substring(0, 12) : '-') : (t.vultr_instance_id || '-')}</td>
            <td class="p-6">
                <div class="flex items-center gap-1.5">
                    ${t.status === 'active' ? html`
                        <button @click=${() => this.tenantAction(t.id, 'suspend', t.name)} title="Detener" class="p-2 rounded-lg hover:bg-red-500/10 text-red-400 transition" ?disabled=${this.actionLoading === t.id + '-suspend'}>
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2" stroke-width="2"/></svg>
                        </button>
                        <button @click=${() => this.tenantAction(t.id, 'restart', t.name)} title="Reiniciar" class="p-2 rounded-lg hover:bg-amber-500/10 text-amber-400 transition" ?disabled=${this.actionLoading === t.id + '-restart'}>
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                        </button>
                    ` : t.status === 'suspended' ? html`
                        <button @click=${() => this.tenantAction(t.id, 'reactivate', t.name)} title="Iniciar" class="p-2 rounded-lg hover:bg-emerald-500/10 text-emerald-400 transition">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21" stroke-width="2" stroke-linejoin="round"/></svg>
                        </button>
                    ` : ''}
                    <button @click=${() => this.viewLogs(t.id, t.name)} title="Logs" class="p-2 rounded-lg hover:bg-brand-blue/10 text-brand-blue transition">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                    </button>
                </div>
            </td>
        </tr>
    `;
}
