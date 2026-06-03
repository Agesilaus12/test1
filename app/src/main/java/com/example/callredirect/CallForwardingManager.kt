package com.example.callredirect

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.content.edit

/**
 * Drives carrier-level **conditional "no reply"** call forwarding via standard GSM
 * MMI codes. Incoming calls ring the phone normally; if they are not answered within
 * the configured no-reply timer, the network forwards them to the target number.
 *
 * No app-side telephony API can transfer an already-ringing call to a third party, so
 * the carrier network is the only place this can happen reliably. This class just
 * submits the supplementary-service codes the network understands.
 *
 * MMI codes (GSM/UMTS supplementary service 61 = "call forwarding on no reply"):
 *   Enable  :  **61*<number>**<seconds>#   (seconds = no-reply timer)
 *   Disable :  ##61#
 *   Query   :  *#61#
 *
 * The no-reply timer is expressed in seconds and the network only accepts values
 * from 5 to 30 in steps of 5. A single ring is ~5 seconds, so the app lets the user
 * think in "rings" and converts: seconds = rings * SECONDS_PER_RING (clamped).
 *
 * Support depends on the carrier and SIM; CDMA-only networks may not honour these.
 */
object CallForwardingManager {

    /** The destination calls are forwarded to when unanswered. */
    const val DEFAULT_TARGET = "+13322324951"

    /** Default number of rings before a call is forwarded. */
    const val DEFAULT_RINGS = 5

    /** Approximate length of one ring cycle, in seconds. */
    const val SECONDS_PER_RING = 5

    /** Network-imposed bounds on the no-reply timer (seconds). */
    const val MIN_SECONDS = 5
    const val MAX_SECONDS = 30
    private const val STEP_SECONDS = 5

    val MIN_RINGS = MIN_SECONDS / SECONDS_PER_RING   // 1
    val MAX_RINGS = MAX_SECONDS / SECONDS_PER_RING   // 6

    private const val PREFS = "call_redirect_prefs"
    private const val KEY_TARGET = "target_number"
    private const val KEY_RINGS = "ring_count"
    private const val KEY_ENABLED = "forwarding_enabled"

    fun getTarget(context: Context): String =
        prefs(context).getString(KEY_TARGET, DEFAULT_TARGET) ?: DEFAULT_TARGET

    fun setTarget(context: Context, number: String) =
        prefs(context).edit { putString(KEY_TARGET, sanitize(number)) }

    fun getRings(context: Context): Int =
        prefs(context).getInt(KEY_RINGS, DEFAULT_RINGS).coerceIn(MIN_RINGS, MAX_RINGS)

    fun setRings(context: Context, rings: Int) =
        prefs(context).edit { putInt(KEY_RINGS, rings.coerceIn(MIN_RINGS, MAX_RINGS)) }

    fun isEnabled(context: Context): Boolean =
        prefs(context).getBoolean(KEY_ENABLED, false)

    private fun setEnabled(context: Context, enabled: Boolean) =
        prefs(context).edit { putBoolean(KEY_ENABLED, enabled) }

    /** Convert a ring count to the nearest network-legal no-reply timer in seconds. */
    fun ringsToSeconds(rings: Int): Int {
        val raw = rings * SECONDS_PER_RING
        val stepped = (Math.round(raw / STEP_SECONDS.toFloat()) * STEP_SECONDS)
        return stepped.coerceIn(MIN_SECONDS, MAX_SECONDS)
    }

    /**
     * Dials `**61*<number>**<seconds>#`. The telephony stack intercepts the MMI string
     * and asks the network to switch on no-reply forwarding. Requires CALL_PHONE.
     */
    fun enableForwarding(context: Context) {
        val number = getTarget(context)
        val seconds = ringsToSeconds(getRings(context))
        val mmi = "**61*$number**$seconds#"
        dialMmi(context, mmi)
        setEnabled(context, true)
    }

    /** Dials `##61#` to cancel no-reply forwarding. Requires CALL_PHONE. */
    fun disableForwarding(context: Context) {
        dialMmi(context, "##61#")
        setEnabled(context, false)
    }

    /** Dials `*#61#` so the network shows the current no-reply forwarding status. */
    fun queryForwarding(context: Context) = dialMmi(context, "*#61#")

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
