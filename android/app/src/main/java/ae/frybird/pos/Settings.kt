package ae.frybird.pos

import android.content.Context

class Settings(context: Context) {
    private val prefs = context.getSharedPreferences("frybird", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString("server", "https://pos.frybird.ae")!!
        set(value) = prefs.edit().putString("server", value.trim().trimEnd('/')).apply()

    // /pos on the counter terminal, /pos/captain on waiters' tablets.
    var startPage: String
        get() = prefs.getString("start", "/pos")!!
        set(value) = prefs.edit().putString("start", "/" + value.trim().trimStart('/')).apply()

    var kitchenPrinterIp: String
        get() = prefs.getString("printer", "192.168.123.100")!!
        set(value) = prefs.edit().putString("printer", value.trim()).apply()

    var apiKey: String
        get() = prefs.getString("key", "")!!
        set(value) = prefs.edit().putString("key", value.trim()).apply()

    var apiSecret: String
        get() = prefs.getString("secret", "")!!
        set(value) = prefs.edit().putString("secret", value.trim()).apply()

    // Only the counter terminal has these, so tablets don't print every ticket a second time.
    val kitchenConfigured get() = apiKey.isNotEmpty() && apiSecret.isNotEmpty()
}
