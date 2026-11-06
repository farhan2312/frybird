package ae.frybird.pos

import org.json.JSONArray
import java.io.ByteArrayOutputStream

/** Turns a print document from the server (see ury/ury/api/kitchen_print.py) into printer commands. */
object EscPos {
    private val INIT = byteArrayOf(0x1B, 0x40)
    private val FEED = byteArrayOf(0x1B, 0x64, 0x05)
    private val CUT = byteArrayOf(0x1D, 0x56, 0x00)

    fun render(lines: JSONArray, cut: Boolean): ByteArray {
        val out = ByteArrayOutputStream()
        out.write(INIT)
        for (i in 0 until lines.length()) {
            val line = lines.getJSONObject(i)
            val align = when (line.optString("a", "l")) {
                "c" -> 1
                "r" -> 2
                else -> 0
            }
            out.write(byteArrayOf(0x1B, 0x61, align.toByte()))
            out.write(byteArrayOf(0x1B, 0x45, if (line.optBoolean("b")) 1 else 0))
            val size = when (line.optInt("s", 1)) {
                2 -> 0x11 // double height and width
                3 -> 0x01 // double height only, so a line still fits as many characters
                else -> 0x00
            }
            out.write(byteArrayOf(0x1D, 0x21, size.toByte()))
            out.write(line.optString("t").toByteArray(Charsets.US_ASCII))
            out.write(0x0A)
        }
        out.write(FEED)
        if (cut) out.write(CUT)
        return out.toByteArray()
    }

    fun testDocument(title: String): JSONArray {
        val line = { text: String, bold: Boolean, size: Int ->
            org.json.JSONObject().put("t", text).put("b", bold).put("s", size).put("a", "c")
        }
        return JSONArray().put(line(title, true, 2)).put(line("FryBird POS test print", false, 1))
    }
}
