package ae.frybird.pos

import android.app.Activity
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.webkit.WebView
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast

/** Printer and server details, plus test prints for checking a new install. */
class SettingsActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val settings = Settings(this)
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 32, 48, 32)
        }
        val field = { label: String, value: String, secret: Boolean ->
            layout.addView(TextView(this).apply { text = label; setPadding(0, 24, 0, 0) })
            EditText(this).apply {
                setText(value)
                setSingleLine()
                inputType = InputType.TYPE_CLASS_TEXT or
                    if (secret) InputType.TYPE_TEXT_VARIATION_PASSWORD else InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
                layout.addView(this)
            }
        }
        val server = field("Server address", settings.serverUrl, false)
        val startPage = field("Start page (/pos on the counter, /pos/captain on tablets)", settings.startPage, false)
        val printer = field("Kitchen printer IP", settings.kitchenPrinterIp, false)
        val key = field("Print API key (counter terminal only)", settings.apiKey, false)
        val secret = field("Print API secret", settings.apiSecret, true)

        val save = {
            settings.serverUrl = server.text.toString()
            settings.startPage = startPage.text.toString()
            settings.kitchenPrinterIp = printer.text.toString()
            settings.apiKey = key.text.toString()
            settings.apiSecret = secret.text.toString()
            if (settings.kitchenConfigured) KitchenPrintService.start(this)
        }
        val result = TextView(this).apply { setPadding(0, 24, 0, 24); textSize = 16f }
        val button = { label: String, action: () -> Unit ->
            layout.addView(Button(this).apply { text = label; setOnClickListener { action() } })
        }

        button("Save") {
            save()
            Toast.makeText(this, "Saved", Toast.LENGTH_SHORT).show()
            finish()
        }
        button("Test kitchen printer") {
            save()
            result.text = "Printing..."
            Thread {
                val message = try {
                    KitchenPrinter.print(settings.kitchenPrinterIp, EscPos.testDocument("KITCHEN PRINTER"))
                    "Kitchen printer: sent. Check a slip came out and cut."
                } catch (e: Exception) {
                    "Kitchen printer failed: ${e.message}"
                }
                runOnUiThread { result.text = message }
            }.start()
        }
        button("Test built-in receipt printer") {
            val error = CounterPrinter.print(EscPos.testDocument("BUILT-IN PRINTER"))
            result.text = error.ifEmpty { "Built-in printer: sent. Check a slip came out and cut." }
        }
        layout.addView(result)

        val webViewVersion = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) WebView.getCurrentWebViewPackage()?.versionName else null
        layout.addView(TextView(this).apply {
            text = "Android ${Build.VERSION.RELEASE}, ${Build.MODEL}, browser engine ${webViewVersion ?: "unknown"}"
        })
        setContentView(ScrollView(this).apply { addView(layout) })
    }
}
