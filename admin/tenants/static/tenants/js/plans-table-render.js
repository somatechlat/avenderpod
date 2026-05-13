import { html } from '/static/tenants/vendor/lit-core-3.min.js';

/**
 * Render a single plan row for the SaaS Plans table.
 * Called with `this` bound to the MasterControlPlane instance.
 *
 * @param {object} p - Plan object from the API.
 * @returns {import('lit').TemplateResult}
 */
export function renderPlanRow(p) {
    return html`
        <tr class="hover:bg-white/5 transition duration-200">
            <td class="p-6">
                <p class="font-bold text-white text-lg">${p.name} ${!p.is_active ? html`<span class="text-xs text-slate-500 ml-2">Inactivo</span>` : ''}</p>
                <p class="text-xs text-slate-500 mt-1">${p.description || p.slug}</p>
            </td>
            <td class="p-6 text-brand-blue font-bold">${p.is_custom_priced ? 'A medida' : `$${p.price_monthly}/mes`}</td>
            <td class="p-6 text-slate-400 text-sm">${p.max_conversations} conv. / ${p.max_messages_per_day} msg-dia / ${p.max_numbers} WA</td>
            <td class="p-6 text-slate-400 text-sm">${[
                p.allow_mobile_app ? 'App' : '',
                p.allow_voice_messages ? 'Audios' : '',
                p.allow_multichannel ? 'Multicanal' : '',
                p.allow_integrations ? 'Integraciones' : '',
                p.allow_call_handling ? 'Llamadas' : ''
            ].filter(Boolean).join(', ') || 'Basico'}</td>
            <td class="p-6">
                <div class="flex gap-2">
                    <button @click=${() => this.openPlanWizard('edit', p)} title="Editar" class="p-2 rounded-lg hover:bg-brand-blue/10 text-brand-blue transition">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
                    </button>
                    <button @click=${() => this.deletePlan(p.id)} title="Eliminar" class="p-2 rounded-lg hover:bg-brand-pink/10 text-brand-pink transition">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                    </button>
                </div>
            </td>
        </tr>
    `;
}
