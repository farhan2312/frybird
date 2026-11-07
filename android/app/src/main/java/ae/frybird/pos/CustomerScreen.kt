package ae.frybird.pos

import android.annotation.SuppressLint
import android.app.Activity
import android.app.Presentation
import android.content.Context
import android.hardware.display.DisplayManager
import android.os.Bundle
import android.view.Display
import android.webkit.WebView
import android.webkit.WebViewClient
import org.json.JSONObject

/** The T2s's customer-facing screen. It shows a page from the server, so its layout changes without a new app. */
class CustomerScreen(activity: Activity, display: Display, private val pageUrl: String) : Presentation(activity, display) {
    private var webView: WebView? = null
    private var pageReady = false
    private var latestOrder: String? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        webView = WebView(context).apply {
            settings.javaScriptEnabled = true
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView, url: String) {
                    pageReady = true
                    send()
                }
            }
            loadUrl(pageUrl)
        }
        setContentView(webView!!)
    }

    /** Takes the order as JSON from the POS page. Call on the main thread. */
    fun showOrder(order: String) {
        latestOrder = JSONObject(order).toString()
        send()
    }

    private fun send() {
        val order = latestOrder ?: return
        if (pageReady) webView?.evaluateJavascript("window.showCart($order)", null)
    }

    companion object {
        fun findDisplay(context: Context): Display? =
            (context.getSystemService(Context.DISPLAY_SERVICE) as DisplayManager)
                .getDisplays(DisplayManager.DISPLAY_CATEGORY_PRESENTATION)
                .firstOrNull()
    }
}
