import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// The signing key stays out of the repo; updates must be signed with the same key to install over the old app.
val signing = Properties().apply {
    val file = File(System.getProperty("user.home"), "android-tools/frybird-signing.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

android {
    namespace = "ae.frybird.pos"
    compileSdk = 34

    defaultConfig {
        applicationId = "ae.frybird.pos"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    signingConfigs {
        if (signing.isNotEmpty()) {
            create("release") {
                storeFile = File(signing.getProperty("storeFile"))
                storePassword = signing.getProperty("storePassword")
                keyAlias = signing.getProperty("keyAlias")
                keyPassword = signing.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (signing.isNotEmpty()) signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("com.sunmi:printerlibrary:1.0.24")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
