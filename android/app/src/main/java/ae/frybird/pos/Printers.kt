package ae.frybird.pos

import android.content.Context
import com.sunmi.peripheral.printer.InnerPrinterCallback
import com.sunmi.peripheral.printer.InnerPrinterManager
import com.sunmi.peripheral.printer.SunmiPrinterService
import org.json.JSONArray
import java.net.InetSocketAddress
import java.net.Socket

/** The kitchen printer, on the shop network. */
object KitchenPrinter {
    private const val PORT = 9100
    private const val TIMEOUT_MS = 5000

    fun print(host: String, lines: JSONArray) {
        Socket().use { socket ->
            socket.soTimeout = TIMEOUT_MS
            socket.connect(InetSocketAddress(host, PORT), TIMEOUT_MS)
            socket.getOutputStream().apply {
                write(EscPos.render(lines, cut = true))
                flush()
            }
        }
    }
}

/** The printer built into the SUNMI terminal, used for counter receipts. */
object CounterPrinter {
    @Volatile
    private var service: SunmiPrinterService? = null

    fun connect(context: Context) {
        try {
            InnerPrinterManager.getInstance().bindService(context.applicationContext, object : InnerPrinterCallback() {
                override fun onConnected(printer: SunmiPrinterService) {
                    service = printer
                }

                override fun onDisconnected() {
                    service = null
                }
            })
        } catch (e: Exception) {
            service = null
        }
    }

    /** Returns an error message, or "" when the receipt was sent to the printer. */
    fun print(lines: JSONArray): String {
        val printer = service ?: return "The built-in printer isn't ready. Check it's on this SUNMI terminal, then try again."
        return try {
            printer.sendRAWData(EscPos.render(lines, cut = false), null)
            printer.cutPaper(null)
            ""
        } catch (e: Exception) {
            "Couldn't print the receipt: ${e.message}"
        }
    }
}
