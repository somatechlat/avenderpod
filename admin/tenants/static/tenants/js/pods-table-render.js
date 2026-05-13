import { html } from '/static/tenants/vendor/lit-core-3.min.js';

/**
 * Render a single pod row for the Avender Pods table.
 * Called with `this` bound to the MasterControlPlane instance.
 *
 * @param {object} p - PodDeployment object from the API.
 * @returns {import('lit').TemplateResult}
 */
export function renderPodRow(p) {
    return html`
        <tr class="hover:bg-white/5 transition duration-200">
            <td class="p-6">
                <p class="font-bold text-white">${p.pod_name}</p>
                <p class="text-xs text-slate-500 mt-1">${p.tenant_name}</p>
                <p class="text-[10px] text-slate-600 font-mono mt-1">${p.image_tag || '-'}</p>
            </td>
            <td class="p-6">
                ${p.deployment_backend === 'docker' ? html`
                    <span class="px-2.5 py-1 text-[10px] font-bold rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">DOCKER</span>
                ` : html`
                    <span class="px-2.5 py-1 text-[10px] font-bold rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20">VULTR</span>
                `}
                <p class="text-[10px] text-slate-500 font-mono mt-2">${p.assigned_port || '-'}</p>
            </td>
            <td class="p-6">
                <span class="px-3 py-1.5 text-xs font-bold rounded-full border ${p.lifecycle_state === 'active' ? 'bg-brand-cyan/10 text-brand-cyan border-brand-cyan/20' : p.lifecycle_state === 'suspended' || p.lifecycle_state === 'stopped' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-brand-pink/10 text-brand-pink border-brand-pink/20'}">${p.lifecycle_state.toUpperCase()}</span>
                ${p.last_error ? html`<p class="text-xs text-brand-pink mt-2 max-w-xs break-words">${p.last_error}</p>` : ''}
            </td>
            <td class="p-6 text-sm text-slate-400">
                ${p.provider_health_state}
                <p class="text-[10px] text-slate-600 mt-1">${p.last_health_check_at ? new Date(p.last_health_check_at).toLocaleString() : '-'}</p>
            </td>
            <td class="p-6 text-sm text-slate-400">${p.tenant_vault_state}</td>
            <td class="p-6 text-xs text-slate-400">
                <p>${p.effective_rate_limits?.A0_MAX_MESSAGES_PER_DAY || '-'} msg/dia</p>
                <p>${p.effective_rate_limits?.A0_MAX_MESSAGES_PER_MINUTE || '-'} msg/min</p>
                <p>${p.effective_rate_limits?.A0_MAX_WHATSAPP_NUMBERS || '-'} WA</p>
            </td>
            <td class="p-6">
                <div class="flex items-center gap-1.5">
                    <button @click=${() => this.podAction(p.id, 'refresh-health')} title="Refresh Health" class="p-2 rounded-lg hover:bg-brand-blue/10 text-brand-blue transition" ?disabled=${this.actionLoading === p.id + '-refresh-health'}>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v6h6M20 20v-6h-6M5 19A9 9 0 0119 5"/></svg>
                    </button>
                    ${p.lifecycle_state === 'active' ? html`
                        <button @click=${() => this.podAction(p.id, 'stop')} title="Stop" class="p-2 rounded-lg hover:bg-amber-500/10 text-amber-400 transition" ?disabled=${this.actionLoading === p.id + '-stop'}>
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2" stroke-width="2"/></svg>
                        </button>
                        <button @click=${() => this.podAction(p.id, 'suspend')} title="Suspend" class="p-2 rounded-lg hover:bg-red-500/10 text-red-400 transition" ?disabled=${this.actionLoading === p.id + '-suspend'}>
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6M5 12a7 7 0 1014 0 7 7 0 00-14 0z"/></svg>
                        </button>
                    ` : html`
                        <button @click=${() => this.podAction(p.id, 'reactivate')} title="Reactivate" class="p-2 rounded-lg hover:bg-emerald-500/10 text-emerald-400 transition" ?disabled=${this.actionLoading === p.id + '-reactivate'}>
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21" stroke-width="2" stroke-linejoin="round"/></svg>
                        </button>
                    `}
                    <button @click=${() => this.podAction(p.id, 'restart')} title="Restart" class="p-2 rounded-lg hover:bg-amber-500/10 text-amber-400 transition" ?disabled=${this.actionLoading === p.id + '-restart'}>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                    </button>
                    <button @click=${() => this.viewPodLogs(p.id, p.pod_name)} title="Logs" class="p-2 rounded-lg hover:bg-brand-blue/10 text-brand-blue transition">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                    </button>
                    <button @click=${() => this.podAction(p.id, '', 'DELETE')} title="Delete" class="p-2 rounded-lg hover:bg-brand-pink/10 text-brand-pink transition" ?disabled=${this.actionLoading === p.id + '-'}>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                    </button>
                </div>
            </td>
        </tr>
    `;
}
