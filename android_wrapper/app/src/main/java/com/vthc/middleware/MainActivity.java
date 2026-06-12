package com.vthc.middleware;

import android.os.Bundle;
import android.util.Log;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

public class MainActivity extends AppCompatActivity {
    private static final String TAG = "MainActivity";
    private static final String URL_PRIMARY = "http://127.0.0.1:5000/";
    private static final String URL_FALLBACK = "http://127.0.0.1:5001/";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }

        new Thread(() -> {
            Python py = Python.getInstance();
            py.getModule("main").callAttr("run_server");
        }).start();

        WebView webView = findViewById(R.id.webview);
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setAllowFileAccess(true);
        webView.setWebViewClient(new WebViewClient() {
            private boolean didFallback = false;

            @Override
            public void onReceivedError(@NonNull WebView view, @NonNull WebResourceRequest request, @NonNull WebResourceError error) {
                Log.w(TAG, "WebView error " + error.getErrorCode() + " for " + request.getUrl());
                if (!didFallback && URL_PRIMARY.equals(request.getUrl().toString())) {
                    didFallback = true;
                    Log.i(TAG, "Primary port failed, retrying fallback port.");
                    view.loadUrl(URL_FALLBACK);
                }
            }
        });

        // Delay initial load to allow the Python server time to start.
        webView.postDelayed(() -> webView.loadUrl(URL_PRIMARY), 5000);
    }
}
