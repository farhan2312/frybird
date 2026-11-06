package ae.frybird.pos

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.media.AudioManager
import android.media.ToneGenerator
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject

/** Shows the POS website full screen and connects it to the printers. */
class MainActivity : Activity() {
    private lateinit var webView: WebView
    private lateinit var banner: TextView
    private val handler = Handler(Looper.getMainLooper())
    private val alarm by lazy { ToneGenerator(AudioManager.STREAM_ALARM, 100) }
    private var checks = 0

    private val statusCheck = object : Runnable {
        override fun run() {
            val problem = KitchenStatus.problem
            banner.text = problem
            banner.visibility = if (problem == null) TextView.GONE else TextView.VISIBLE
            // Missed tickets mean missed orders, so make sure someone notices.
            if (KitchenStatus.ticketsWaiting && checks++ % ALARM_EVERY_CHECKS == 0) {
                alarm.startTone(ToneGenerator.TONE_CDMA_ALERT_CALL_GUARD, 1000)
            }
            handler.postDelayed(this, CHECK_MS)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val prefs = Settings(this)

        banner = TextView(this).apply {
            setBackgroundColor(Color.parseColor("#C62828"))
            setTextColor(Color.WHITE)
            textSize = 18f
            gravity = Gravity.CENTER
            setPadding(24, 16, 24, 16)
            visibility = TextView.GONE
            setOnClickListener { startActivity(Intent(this@MainActivity, SettingsActivity::class.java)) }
        }
        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            addJavascriptInterface(PrinterBridge(), "FryBirdPrinter")
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    return request.url.host != Uri.parse(prefs.serverUrl).host
                }
            }
        }
        val settingsButton = TextView(this).apply {
            text = "⚙"
            textSize = 22f
            setTextColor(Color.GRAY)
            setPadding(16, 4, 16, 4)
            setOnClickListener { startActivity(Intent(this@MainActivity, SettingsActivity::class.java)) }
        }
        val content = FrameLayout(this).apply {
            addView(webView, FrameLayout.LayoutParams(MATCH_PARENT, MATCH_PARENT))
            addView(settingsButton, FrameLayout.LayoutParams(WRAP_CONTENT, WRAP_CONTENT, Gravity.BOTTOM or Gravity.START))
        }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            addView(banner, LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT))
            addView(content, LinearLayout.LayoutParams(MATCH_PARENT, 0, 1f))
        })

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 0)
        CounterPrinter.connect(this)
        if (prefs.kitchenConfigured) KitchenPrintService.start(this)
        webView.loadUrl(prefs.serverUrl + prefs.startPage)
    }

    override fun onResume() {
        super.onResume()
        handler.post(statusCheck)
    }

    override fun onPause() {
        handler.removeCallbacks(statusCheck)
        super.onPause()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack()
    }

    private class PrinterBridge {
        @JavascriptInterface
        fun printReceipt(document: String): String = try {
            CounterPrinter.print(JSONObject(document).getJSONArray("lines"))
        } catch (e: Exception) {
            "Couldn't read the receipt: ${e.message}"
        }
    }

    companion object {
        private const val CHECK_MS = 1000L
        private const val ALARM_EVERY_CHECKS = 15
    }
}
