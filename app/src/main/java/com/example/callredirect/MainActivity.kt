package com.example.callredirect

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.example.callredirect.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    private val requestPermissions =
        registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
            val granted = result.values.all { it }
            if (granted) {
                Toast.makeText(this, R.string.permissions_granted, Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, R.string.permissions_needed, Toast.LENGTH_LONG).show()
            }
            refreshStatus()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.targetInput.setText(CallForwardingManager.getTarget(this))

        binding.enableButton.setOnClickListener {
            if (!ensurePermissions()) return@setOnClickListener
            CallForwardingManager.setTarget(this, binding.targetInput.text.toString())
            CallForwardingManager.enableForwarding(this)
            refreshStatus()
        }

        binding.disableButton.setOnClickListener {
            if (!ensurePermissions()) return@setOnClickListener
            CallForwardingManager.disableForwarding(this)
            refreshStatus()
        }

        binding.queryButton.setOnClickListener {
            if (!ensurePermissions()) return@setOnClickListener
            CallForwardingManager.queryForwarding(this)
        }

        refreshStatus()
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    private fun refreshStatus() {
        val enabled = CallForwardingManager.isEnabled(this)
        val target = CallForwardingManager.getTarget(this)
        binding.statusText.text = if (enabled) {
            getString(R.string.status_on, target)
        } else {
            getString(R.string.status_off)
        }
    }

    /** @return true if all required permissions are already granted. */
    private fun ensurePermissions(): Boolean {
        val needed = REQUIRED_PERMISSIONS.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isEmpty()) return true
        requestPermissions.launch(needed.toTypedArray())
        return false
    }

    companion object {
        private val REQUIRED_PERMISSIONS = arrayOf(
            Manifest.permission.CALL_PHONE,
            Manifest.permission.READ_PHONE_STATE,
        )
    }
}
