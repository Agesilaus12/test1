# Call Redirect

An Android app that redirects **every incoming call** on the phone to another
number — by default **+1 332-232-4951**.

## How it works (read this first)

Android has **no API that lets an app grab a ringing call and bridge it to a
third party.** Any app claiming to "intercept and re-route" a live call is
either using accessibility hacks that break constantly, or simply rejecting the
call (which drops the caller, it does not forward them).

The mechanism that genuinely forwards *every* call is **carrier-level
unconditional call forwarding**. It runs inside the mobile network, so calls are
re-routed to the target number *before the device ever rings*. Phones expose
this through standard GSM MMI codes:

| Action  | Code            |
|---------|-----------------|
| Enable  | `**21*<number>#` |
| Disable | `##21#`         |
| Status  | `*#21#`         |

This app is a friendly front-end that dials those codes for you and remembers
the target number.

- **Enable forwarding** → dials `**21*+13322324951#`
- **Disable forwarding** → dials `##21#`
- **Check status** → dials `*#21#`

The on-device phone number (e.g. `438-680-8599`) does not need to be configured;
the app simply runs on that handset and switches its own forwarding on/off.

## Requirements & limitations

- The SIM/carrier must support unconditional call forwarding (most GSM/UMTS/LTE
  carriers do; some CDMA networks do not).
- Carriers may bill for forwarded calls — check your plan.
- Requires the `CALL_PHONE` permission so the app can submit the MMI code, and
  `READ_PHONE_STATE` for the optional call-detection hook.
- Only configure forwarding on a phone you are authorised to manage.

## Project layout

```
app/src/main/
├── AndroidManifest.xml
├── java/com/example/callredirect/
│   ├── MainActivity.kt            # UI: set target, enable/disable/query
│   ├── CallForwardingManager.kt   # dials the MMI codes, stores settings
│   └── CallReceiver.kt            # optional ringing-call observer (logging only)
└── res/                           # layout, strings, theme, launcher icon
```

## Building

Open the project in **Android Studio** (Hedgehog or newer) and click Run, or
from the command line with the Android SDK installed:

```bash
./gradlew assembleDebug
# APK appears at app/build/outputs/apk/debug/app-debug.apk
```

Set the SDK location via `local.properties` (`sdk.dir=/path/to/Android/sdk`) or
the `ANDROID_HOME` environment variable.

- `minSdk` 26 (Android 8.0) · `targetSdk` 34 · Kotlin · Material 3
