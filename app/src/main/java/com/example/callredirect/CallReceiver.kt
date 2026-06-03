package com.example.callredirect

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.TelephonyManager
import android.util.Log

/**
 * Optional, best-effort fallback that observes phone-state changes.
 *
 * IMPORTANT: a BroadcastReceiver CANNOT transfer a ringing call to another number.
 * Android exposes no API to bridge an in-progress incoming call to a third party.
 * The only thing that genuinely redirects *every* call is the carrier-level
 * unconditional forwarding enabled by [CallForwardingManager].
 *
 * This receiver therefore only logs ringing events. It exists so that, if a device
 * or carrier ever silently drops the forwarding rule, the app still has a hook
 * point to surface that a call came through unforwarded (e.g. notify the user).
 */
class CallReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return

        val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)
        if (state == TelephonyManager.EXTRA_STATE_RINGING) {
            val incoming = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER)
            val forwardingOn = CallForwardingManager.isEnabled(context)
            Log.i(
                TAG,
                "Incoming call from ${incoming ?: "unknown"}; " +
                    "network forwarding ${if (forwardingOn) "ENABLED" else "DISABLED"}."
            )
            // If forwarding is enabled at the network level, this call has already
            // been routed to the target before reaching the device. Nothing to do.
        }
    }

    companion object {
        private const val TAG = "CallReceiver"
    }
}
