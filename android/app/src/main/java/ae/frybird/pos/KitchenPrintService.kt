package ae.frybird.pos

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** What the counter screen shows when kitchen tickets aren't printing. Null means all is well. */
object KitchenStatus {
    @Volatile
    var problem: String? = null

    @Volatile
    var ticketsWaiting = false
}

/** Keeps collecting kitchen tickets from the server and printing them, whatever the POS screen is doing. */
class KitchenPrintService : Service() {
    private var worker: Thread? = null

    // Printed but not yet confirmed to the server, so a dropped connection can't print a ticket twice.
    private val printedNotConfirmed = mutableSetOf<String>()

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, notification())
        if (worker?.isAlive != true) {
            worker = Thread(::run, "kitchen-print").apply { start() }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        worker?.interrupt()
        super.onDestroy()
    }

    private fun run() {
        val settings = Settings(this)
        var serverFailures = 0
        while (!Thread.currentThread().isInterrupted) {
            if (settings.kitchenConfigured) {
                try {
                    printPending(settings)
                    serverFailures = 0
                } catch (e: PrinterError) {
                    KitchenStatus.ticketsWaiting = true
                    KitchenStatus.problem = "Kitchen printer not responding (${settings.kitchenPrinterIp}). Tickets are waiting: check its power, paper and cable."
                } catch (e: Exception) {
                    // A brief internet drop is normal, so only warn once it has lasted a few tries.
                    if (++serverFailures >= SERVER_FAILURES_BEFORE_WARNING) {
                        KitchenStatus.ticketsWaiting = false
                        KitchenStatus.problem = "Can't reach the server, so kitchen tickets may not print. Check the internet."
                    }
                }
            } else {
                KitchenStatus.ticketsWaiting = false
                KitchenStatus.problem = null
            }
            try {
                Thread.sleep(POLL_MS)
            } catch (e: InterruptedException) {
                return
            }
        }
    }

    private fun printPending(settings: Settings) {
        val tickets = call(settings, "GET", "get_pending_tickets").getJSONArray("message")
        for (i in 0 until tickets.length()) {
            val ticket = tickets.getJSONObject(i)
            val kots = ticket.getJSONArray("kots")
            val id = kots.toString()
            if (id !in printedNotConfirmed) {
                try {
                    KitchenPrinter.print(settings.kitchenPrinterIp, ticket.getJSONArray("lines"), EscPos.fromHex(ticket.optString("beep")))
                } catch (e: Exception) {
                    throw PrinterError(e)
                }
                printedNotConfirmed.add(id)
            }
            call(settings, "POST", "mark_tickets_printed", "kots=" + URLEncoder.encode(id, "UTF-8"))
            printedNotConfirmed.remove(id)
        }
        KitchenStatus.ticketsWaiting = false
        KitchenStatus.problem = null
    }

    private fun call(settings: Settings, method: String, function: String, body: String? = null): JSONObject {
        val url = URL("${settings.serverUrl}/api/method/ury.ury.api.kitchen_print.$function")
        val connection = url.openConnection() as HttpURLConnection
        try {
            connection.requestMethod = method
            connection.connectTimeout = TIMEOUT_MS
            connection.readTimeout = TIMEOUT_MS
            connection.setRequestProperty("Authorization", "token ${settings.apiKey}:${settings.apiSecret}")
            connection.setRequestProperty("Accept", "application/json")
            if (body != null) {
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
                connection.outputStream.use { it.write(body.toByteArray()) }
            }
            if (connection.responseCode != 200) throw RuntimeException("Server replied ${connection.responseCode}")
            return JSONObject(connection.inputStream.bufferedReader().use { it.readText() })
        } finally {
            connection.disconnect()
        }
    }

    private fun notification(): Notification {
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(NotificationChannel(CHANNEL_ID, "Kitchen printing", NotificationManager.IMPORTANCE_LOW))
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        return builder.setSmallIcon(android.R.drawable.ic_menu_send)
            .setContentTitle("FryBird kitchen printing is on")
            .setContentIntent(open)
            .build()
    }

    private class PrinterError(cause: Exception) : Exception(cause)

    companion object {
        private const val CHANNEL_ID = "kitchen"
        private const val NOTIFICATION_ID = 1
        private const val POLL_MS = 3000L
        private const val TIMEOUT_MS = 10000
        private const val SERVER_FAILURES_BEFORE_WARNING = 10

        fun start(context: Context) {
            val intent = Intent(context, KitchenPrintService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent) else context.startService(intent)
        }
    }
}
