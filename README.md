# Call Redirect

An Android app that forwards **unanswered incoming calls** to another number —
by default **+1 332-232-4951** — after a configurable number of rings.

## How it works (read this first)

Android has **no API that lets an app grab a ringing call and bridge it to a
third party.** Any app claiming to "intercept and re-route" a live call is
either using accessibility hacks that break constantly, or simply rejecting the
call (which drops the caller, it does not forward them).

The mechanism that genuinely forwards calls is **carrier-level call
forwarding**. It runs inside the mobile network. This app uses the
**"no reply"** variant: the phone rings normally, and only if you don't answer
within the chosen number of rings does the network forward the call. Phones
expose this through standard GSM MMI codes (supplementary service **61**):

| Action  | Code                          |
|---------|-------------------------------|
| Enable  | `**61*<number>**<seconds>#`   |
| Disable | `##61#`                       |
| Status  | `*#61#`                       |

`<seconds>` is the no-reply timer. The network only accepts 5–30 in steps of 5,
and one ring is roughly 5 seconds, so the app lets you set **rings** and converts
(e.g. 5 rings → 25 s).

This app is a friendly front-end that dials those codes for you and remembers
your settings (**target number** and **number of rings**, both editable in-app).

- **Enable forwarding** → dials e.g. `**61*+13322324951**25#`
- **Disable forwarding** → dials `##61#`
- **Check status** → dials `*#61#`

The on-device phone number (e.g. `438-680-8599`) does not need to be configured;
the app simply runs on that handset and switches its own forwarding on/off.

## Requirements & limitations

- The SIM/carrier must support no-reply call forwarding (most GSM/UMTS/LTE
  carriers do; some CDMA networks do not).
- The no-reply timer is rounded to the nearest legal 5-second step (5–30 s), so
  the effective ring count may differ slightly from what you type.
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
