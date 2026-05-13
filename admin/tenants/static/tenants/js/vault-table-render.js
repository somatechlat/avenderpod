import { html } from '/static/tenants/vendor/lit-core-3.min.js';

/**
 * Render a single vault record row for the Vault Security Logs table.
 * Called with `this` bound to the MasterControlPlane instance.
 *
 * @param {object} v - VaultRecord object from the API.
 * @returns {import('lit').TemplateResult}
 */
export function renderVaultRow(v) {
    return html`
        <tr class="hover:bg-white/5 transition duration-200">
            <td class="p-6 text-xs font-mono text-slate-500">${new Date(v.created_at).toLocaleString()}</td>
            <td class="p-6 font-bold text-white">${v.tenant_name}</td>
            <td class="p-6 font-mono text-xs text-brand-cyan">${v.vault_path}</td>
        </tr>
    `;
}
