package com.example.callredirect

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.content.edit

/**
 * Drives carrier-level **unconditional** call forwarding via standard GSM MMI codes.
 *
 * This is the only mechanism on stock Android that reliably redirects *every* incoming
 * call: the redirect happens inside the carrier network, before the device ever rings.
 * No app-side telephony API can transfer an already-ringing call to a third party.
 *
 * MMI codes (GSM/UMTS supplementary services):
 *   Enable  unconditional forwarding :  **21*<number>#
 *   Disable unconditional forwarding :  ##21#
 *   Query   status                   :  *#21#
 *
 * Support depends on the carrier and SIM; CDMA-only networks may not honour these.
 */
object CallForwardingManager {

    /** The destination every incoming call should be forwarded to. */
    const val DEFAULT_TARGET = "+13322324951"

    private const val PREFS = "call_redirect_prefs"
    private const val KEY_TARGET = "target_number"
    private const val KEY_ENABLED = "forwarding_enabled"

    fun getTarget(context: Context): String =
        prefs(context).getString(KEY_TARGET, DEFAULT_TARGET) ?: DEFAULT_TARGET

    fun setTarget(context: Context, number: String) =
        prefs(context).edit { putString(KEY_TARGET, sanitize(number)) }

    fun isEnabled(context: Context): Boolean =
        prefs(context).getBoolean(KEY_ENABLED, false)

    private fun setEnabled(context: Context, enabled: Boolean) =
        prefs(context).edit { putBoolean(KEY_ENABLED, enabled) }

    /**
     * Dials `**21*<number>#`. The telephony stack intercepts the MMI string and asks
     * the network to switch on unconditional forwarding. Requires CALL_PHONE.
     */
    fun enableForwarding(context: Context) {
        val number = getTarget(context)
        val mmi = "**21*$number#"
        dialMmi(context, mmi)
        setEnabled(context, true)
    }

    /** Dials `##21#` to cancel unconditional forwarding. Requires CALL_PHONE. */
    fun disableForwarding(context: Context) {
        dialMmi(context, "##21#")
        setEnabled(context, false)
    }

    /** Dials `*#21#` so the network shows the current forwarding status. */
    fun queryForwarding(context: Context) = dialMmi(context, "*#21#")

    /**
     * MMI codes contain '#', which is reserved in a tel: URI, so it must be encoded
     * as %23. ACTION_CALL launches the dialer and immediately submits the code.
     */
    private fun dialMmi(context: Context, mmi: String) {
        val encoded = Uri.encode(mmi)
        val intent = Intent(Intent.ACTION_CALL, Uri.parse("tel:$encoded")).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(intent)
    }

    /** Keep digits and a single leading '+'. */
    fun sanitize(raw: String): String {
        val plus = raw.trimStart().startsWith("+")
        val digits = raw.filter { it.isDigit() }
        return if (plus) "+$digits" else digits
    }

    private fun prefs(context: Context) =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
}
