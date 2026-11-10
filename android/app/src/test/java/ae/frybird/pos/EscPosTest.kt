package ae.frybird.pos

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Test

class EscPosTest {
    private val line = JSONObject().put("t", "A").put("b", true).put("s", 2).put("a", "c")

    private fun bytes(vararg values: Int) = values.map { it.toByte() }.toByteArray()

    @Test
    fun rendersStyledLineAndCuts() {
        assertArrayEquals(
            bytes(0x1B, 0x40, 0x1B, 0x61, 1, 0x1B, 0x45, 1, 0x1D, 0x21, 0x11, 0x41, 0x0A, 0x1B, 0x64, 5, 0x1D, 0x56, 0),
            EscPos.render(JSONArray().put(line), cut = true),
        )
    }

    @Test
    fun rendersDoubleHeightLine() {
        val tall = JSONObject().put("t", "A").put("s", 3)
        assertArrayEquals(
            bytes(0x1B, 0x40, 0x1B, 0x61, 0, 0x1B, 0x45, 0, 0x1D, 0x21, 0x01, 0x41, 0x0A, 0x1B, 0x64, 5),
            EscPos.render(JSONArray().put(tall), cut = false),
        )
    }

    @Test
    fun rendersDoubleWidthLine() {
        val wide = JSONObject().put("t", "A").put("s", 4)
        assertArrayEquals(
            bytes(0x1B, 0x40, 0x1B, 0x61, 0, 0x1B, 0x45, 0, 0x1D, 0x21, 0x10, 0x41, 0x0A, 0x1B, 0x64, 5),
            EscPos.render(JSONArray().put(wide), cut = false),
        )
    }

    @Test
    fun readsBeepFromHex() {
        assertArrayEquals(bytes(0x1B, 0x42, 3, 2), EscPos.fromHex("1b420302"))
        assertArrayEquals(bytes(), EscPos.fromHex(""))
    }

    @Test
    fun leavesOutCutForBuiltInPrinter() {
        assertArrayEquals(
            bytes(0x1B, 0x40, 0x1B, 0x61, 1, 0x1B, 0x45, 1, 0x1D, 0x21, 0x11, 0x41, 0x0A, 0x1B, 0x64, 5),
            EscPos.render(JSONArray().put(line), cut = false),
        )
    }
}
