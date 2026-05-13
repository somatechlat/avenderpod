import { html } from '/static/tenants/vendor/lit-core-3.min.js';

/**
 * Render a single interaction row for the Agent Interactions table.
 * Called with `this` bound to the MasterControlPlane instance.
 *
 * @param {object} i - InteractionRecord object from the API.
 * @returns {import('lit').TemplateResult}
 */
export function renderInteractionRow(i) {
    return html`
        <tr class="hover:bg-white/5 transition duration-200">
            <td class="p-6 text-xs font-mono text-slate-500">${new Date(i.created_at).toLocaleString()}</td>
            <td class="p-6 font-bold text-white">${i.tenant_name}</td>
            <td class="p-6 font-medium text-brand-pink">${i.archetype}</td>
            <td class="p-6 font-mono text-xs text-slate-400">${i.customer_wa_id}</td>
            <td class="p-6"><span class="px-3 py-1.5 text-xs font-bold rounded-full border bg-white/5 border-white/10 text-white">${i.status}</span></td>
        </tr>
    `;
}
