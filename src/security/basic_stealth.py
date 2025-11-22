#!/usr/bin/env python3
"""
Basic Stealth Manager for BrowserControL01
==========================================

Essential stealth features and detection avoidance.
"""

import time
import random
import json
from typing import Dict, Any, Optional, List


class BasicStealthManager:
    """Basic stealth management and detection avoidance"""
    
    def __init__(self, config: Any, logger: Any):
        """
        Initializes the BasicStealthManager.

        Args:
            config: The SystemConfig instance.
            logger: The logger instance.
        """
        self.config = config
        self.logger = logger
        self.log_func = self.logger.info if self.logger else print
        self.log_func("BasicStealthManager initialized.")
        self.stealth_checks = {}
        
    def apply_browser_stealth_patches(self, driver) -> bool:
        """Apply essential JavaScript stealth patches to browser"""
        try:
            stealth_script = self._get_stealth_javascript()
            
            # Apply patches via CDP
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": stealth_script
            })
            
            self.log_func("Basic stealth patches applied successfully")
            return True
            
        except Exception as e:
            self.log_func(f"Failed to apply stealth patches: {e}")
            return False
    
    def _get_stealth_javascript(self) -> str:
        """Get JavaScript code for stealth patches"""
        return """
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Spoof WebGL fingerprint
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return '{webgl_vendor}';
            if (parameter === 37446) return '{webgl_renderer}';
            return getParameter.apply(this, arguments);
        };
        
        // Basic Chrome runtime
        if (!window.chrome) {
            window.chrome = {{ runtime: {{}} }};
        }
        
        // Permissions API patching
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = function(parameters) {
            if (parameters.name === 'notifications') {
                return Promise.resolve({{ state: 'default' }});
            }
            return originalQuery.apply(this, arguments);
        };
        
        // Plugin enumeration spoofing
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [{{
                name: 'Chrome PDF Plugin',
                description: 'Portable Document Format',
                filename: 'internal-pdf-viewer'
            }}]
        }});
        """.format(
            webgl_vendor=getattr(self.config, 'webgl_vendor', 'Intel Inc.'),
            webgl_renderer=getattr(self.config, 'webgl_renderer', 'Mesa Intel(R) UHD Graphics')
        )
    
    def check_detection_status(self, driver) -> Dict[str, Any]:
        """Basic detection checks"""
        detection_status = {
            'webdriver_detected': False,
            'chrome_detected': False,
            'automation_detected': False,
            'overall_stealth': 'good'
        }
        
        try:
            # Check webdriver property
            webdriver_result = driver.execute_script("return navigator.webdriver;")
            detection_status['webdriver_detected'] = webdriver_result is not None
            
            # Check Chrome runtime
            chrome_result = driver.execute_script("return !!window.chrome;")
            detection_status['chrome_detected'] = not chrome_result
            
            # Check automation flags
            automation_result = driver.execute_script("""
                return document.documentElement.getAttribute('webdriver') !== null ||
                       window.callPhantom !== undefined ||
                       window._phantom !== undefined;
            """)
            detection_status['automation_detected'] = automation_result
            
            # Overall assessment
            if any([detection_status['webdriver_detected'], 
                   detection_status['automation_detected']]):
                detection_status['overall_stealth'] = 'poor'
            elif detection_status['chrome_detected']:
                detection_status['overall_stealth'] = 'fair'
            
            self.log_func(f"Detection status: {detection_status}")
            
        except Exception as e:
            self.log_func(f"Detection check failed: {e}")
            detection_status['overall_stealth'] = 'unknown'
            
        return detection_status
    
    def randomize_timing(self, base_delay: float = 1.0) -> float:
        """Generate randomized timing for stealth"""
        return base_delay * random.uniform(0.8, 1.3)
    
    def get_stealth_report(self, driver) -> Dict[str, Any]:
        """Generate basic stealth assessment report"""
        report = {
            'timestamp': time.time(),
            'detection_checks': self.check_detection_status(driver),
            'stealth_features': {
                'webdriver_nullified': True,
                'webgl_spoofed': True,
                'chrome_runtime_present': True,
                'permissions_patched': True,
                'plugins_spoofed': True
            },
            'recommendations': []
        }
        
        # Add recommendations based on detection
        detection = report['detection_checks']
        if detection['webdriver_detected']:
            report['recommendations'].append("WebDriver property detected - check stealth patches")
        if detection['automation_detected']:
            report['recommendations'].append("Automation flags detected - review browser setup")
        if detection['chrome_detected']:
            report['recommendations'].append("Chrome runtime missing - verify patches")
            
        return report
    
    def apply_timing_delays(self, action_type: str = "default") -> None:
        """Apply human-like timing delays"""
        delay_map = {
            'default': (0.5, 1.5),
            'fast': (0.1, 0.5),
            'slow': (1.0, 3.0),
            'thinking': (2.0, 5.0)
        }
        
        min_delay, max_delay = delay_map.get(action_type, delay_map['default'])
        delay = random.uniform(min_delay, max_delay)
        
        self.log_func(f"Applying {action_type} delay: {delay:.2f}s")
        time.sleep(delay)

    def get_stealth_scripts(self) -> List[Dict[str, str]]:
        """
        Generates a list of JavaScript snippets to be injected.
        Each snippet is a dictionary with 'name' and 'source'.
        """
        scripts = []
        
        # Script to Spoof navigator.plugins and navigator.mimeTypes
        if getattr(self.config, 'spoof_plugins_mimeTypes', True): # Check if spoofing is enabled in config
            self.log_func("Generating JS for navigator.plugins and mimeTypes spoofing.")
            scripts.append({
                "name": "spoof_navigator_plugins_mimeTypes",
                "source": """
                    (() => {
                        // Simulate common plugins
                        const plugins = [
                            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format', mimeTypes: [{ type: 'application/pdf', suffixes: 'pdf', description: '' },{ type: 'text/pdf', suffixes: 'pdf', description: '' }] },
                            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', mimeTypes: [{ type: 'application/pdf', suffixes: 'pdf', description: '' }] },
                            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '', mimeTypes: [{ type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable' },{ type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable' }] }
                        ];

                        const mimeTypesData = [
                            { type: 'application/pdf', suffixes: 'pdf', description: '', enabledPluginName: 'Chrome PDF Plugin' },
                            { type: 'text/pdf', suffixes: 'pdf', description: '', enabledPluginName: 'Chrome PDF Plugin' },
                            { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable', enabledPluginName: 'Native Client' },
                            { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable', enabledPluginName: 'Native Client' }
                        ];

                        const pluginArray = {
                            length: plugins.length,
                            item: function(index) { return plugins[index]; },
                            namedItem: function(name) { return plugins.find(p => p.name === name) || null; },
                            refresh: function() {}
                        };
                        plugins.forEach(plugin => { pluginArray[plugin.name] = plugin; });
                        Object.setPrototypeOf(pluginArray, PluginArray.prototype);

                        const mimeTypeArray = {
                            length: mimeTypesData.length,
                            item: function(index) { 
                                const mt = mimeTypesData[index];
                                const enabledPlugin = plugins.find(p => p.name === mt.enabledPluginName);
                                return { ...mt, enabledPlugin: enabledPlugin };
                            },
                            namedItem: function(name) { 
                                const mt = mimeTypesData.find(m => m.type === name);
                                if (!mt) return null;
                                const enabledPlugin = plugins.find(p => p.name === mt.enabledPluginName);
                                return { ...mt, enabledPlugin: enabledPlugin };
                            }
                        };
                        mimeTypesData.forEach(mime => { mimeTypeArray[mime.type] = { ...mime, enabledPlugin: plugins.find(p => p.name === mime.enabledPluginName) }; });
                        Object.setPrototypeOf(mimeTypeArray, MimeTypeArray.prototype);

                        Object.defineProperty(navigator, 'plugins', { get: () => pluginArray });
                        Object.defineProperty(navigator, 'mimeTypes', { get: () => mimeTypeArray });
                    })();
                """
            })
        
        # Script to Spoof navigator.hardwareConcurrency
        if hasattr(self.config, 'spoof_hardware_concurrency') and self.config.spoof_hardware_concurrency is not None:
            self.log_func(f"Generating JS for navigator.hardwareConcurrency spoofing (value: {self.config.spoof_hardware_concurrency}).")
            scripts.append({
                "name": "spoof_navigator_hardwareConcurrency",
                "source": f"Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {self.config.spoof_hardware_concurrency} }});"
            })

        # Script to Spoof navigator.deviceMemory
        if hasattr(self.config, 'spoof_device_memory') and self.config.spoof_device_memory is not None:
            self.log_func(f"Generating JS for navigator.deviceMemory spoofing (value: {self.config.spoof_device_memory}).")
            scripts.append({
                "name": "spoof_navigator_deviceMemory",
                "source": f"Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {self.config.spoof_device_memory} }});"
            })

        # Script to Spoof WebGL Vendor and Renderer
        webgl_vendor = getattr(self.config, 'webgl_vendor_override', None) or getattr(self.config, 'webgl_vendor', None)
        webgl_renderer = getattr(self.config, 'webgl_renderer_override', None) or getattr(self.config, 'webgl_renderer', None)
        if webgl_vendor and webgl_renderer:
            self.log_func(f"Generating JS for WebGL spoofing (Vendor: {webgl_vendor}, Renderer: {webgl_renderer}).")
            scripts.append({
                "name": "spoof_webgl_details",
                "source": """
                    (() => {
                        try {
                            const getParameter = HTMLCanvasElement.prototype.getContext('webgl').getParameter;
                            HTMLCanvasElement.prototype.getContext('webgl').getParameter = function(parameter) {
                                // UNMASKED_VENDOR_WEBGL
                                if (parameter === 37445) return '''' + webgl_vendor + '''';
                                // UNMASKED_RENDERER_WEBGL
                                if (parameter === 37446) return '''' + webgl_renderer + '''';
                                return getParameter(parameter);
                            };
                        } catch (e) {
                            console.warn('WebGL spoofing failed:', e);
                        }
                    })();
                """
            })

        # Script to Spoof Permissions API
        if hasattr(self.config, 'permissions_default_granted'): # Check if permission spoofing is configured
            self.log_func("Generating JS for Permissions API spoofing.")
            granted_str = json.dumps(getattr(self.config, 'permissions_default_granted', []))
            denied_str = json.dumps(getattr(self.config, 'permissions_default_denied', []))
            prompt_str = json.dumps(getattr(self.config, 'permissions_default_prompt', []))
            scripts.append({
                "name": "spoof_permissions_api",
                "source": f"""
                    (() => {{
                        const originalQuery = navigator.permissions.query;
                        navigator.permissions.query = (descriptor) => {{
                            const name = descriptor.name;
                            const granted = {granted_str};
                            const denied = {denied_str};
                            const prompt = {prompt_str};
                            if (granted.includes(name)) return Promise.resolve({{ state: 'granted', name: name }});
                            if (denied.includes(name)) return Promise.resolve({{ state: 'denied', name: name }});
                            if (prompt.includes(name)) return Promise.resolve({{ state: 'prompt', name: name }});
                            // Fallback to original or a default prompt for unlisted permissions
                            return originalQuery(descriptor);
                        }};
                    }})();
                """
            })

        # Script for Canvas Noise
        if getattr(self.config, 'enable_canvas_noise', False):
            self.log_func("Generating JS for Canvas fingerprinting noise.")
            scripts.append({
                "name": "canvas_noise",
                "source": """
                    (() => {
                        const originalGetContext = HTMLCanvasElement.prototype.getContext;
                        HTMLCanvasElement.prototype.getContext = function(type, attributes) {
                            if (type === '2d') {
                                const context = originalGetContext.call(this, type, attributes);
                                const originalGetImageData = context.getImageData;
                                context.getImageData = function(x, y, sw, sh) {
                                    const imageData = originalGetImageData.call(this, x, y, sw, sh);
                                    for (let i = 0; i < imageData.data.length; i += 4) {
                                        const noise = Math.floor(Math.random() * 5) - 2; // Tiny noise +/- 2
                                        imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
                                        imageData.data[i+1] = Math.max(0, Math.min(255, imageData.data[i+1] + noise));
                                        imageData.data[i+2] = Math.max(0, Math.min(255, imageData.data[i+2] + noise));
                                    }
                                    return imageData;
                                };
                                return context;
                            }
                            return originalGetContext.call(this, type, attributes);
                        };
                    })();
                """
            })

        # Script for AudioContext Noise/Spoofing
        if getattr(self.config, 'enable_audiocontext_noise', False):
            self.log_func("Generating JS for AudioContext fingerprinting noise.")
            scripts.append({
                "name": "audiocontext_noise",
                "source": """
                    (() => {
                        const originalGetChannelData = AudioBuffer.prototype.getChannelData;
                        AudioBuffer.prototype.getChannelData = function(channel) {
                            const data = originalGetChannelData.call(this, channel);
                            for (let i = 0; i < data.length; i++) {
                                data[i] += (Math.random() - 0.5) * 0.00001; // Tiny noise
                            }
                            return data;
                        };
                        // You might also want to spoof specific properties of AudioContext if known targets
                        // e.g., Object.defineProperty(AudioContext.prototype, 'sampleRate', {{ value: 44100 }});
                    })();
                """
            })
        
        # Script to Disable WebRTC (simple method)
        if getattr(self.config, 'disable_webrtc', False):
            self.log_func("Generating JS to disable WebRTC (RTCPeerConnection).")
            scripts.append({
                "name": "disable_webrtc",
                "source": """
                    (() => {
                        try {
                           Object.defineProperty(window, 'RTCPeerConnection', {{ value: undefined, writable: false }});
                           Object.defineProperty(window, 'webkitRTCPeerConnection', {{ value: undefined, writable: false }});
                           Object.defineProperty(window, 'mozRTCPeerConnection', {{ value: undefined, writable: false }});
                        } catch (e) {
                            console.warn('Failed to fully disable WebRTC', e);
                        }
                    })();
                """
            })

        return scripts

    def get_additional_chrome_options(self) -> List[str]:
        """
        Returns a list of additional Chrome command-line options.
        Useful for flags not directly supported by uc.Chrome parameters or general options.
        """
        options = []
        # Example: options.append('--disable-features=SomeFeatureToDisable')
        # These would be driven by self.config settings.
        self.log_func("Getting additional Chrome options from BasicStealthManager (currently none).")
        return options

    def apply_js_stealth_to_driver(self, driver: Any): # uc.Chrome driver
        """
        Applies JavaScript-based stealth techniques to the initialized driver.
        This method is called *after* the driver is initialized.
        """
        self.log_func("Applying JS-based stealth to driver.")
        stealth_scripts = self.get_stealth_scripts()
        
        for script_info in stealth_scripts:
            try:
                self.log_func(f"Injecting JS script: {script_info['name']}")
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': script_info['source']
                })
            except Exception as e:
                error_msg = f"Failed to inject JS script '{script_info['name']}': {e}"
                if self.logger:
                    self.logger.error(error_msg, exc_info=True)
                else:
                    print(error_msg)
        self.log_func("Finished applying JS-based stealth scripts.")

# Example usage (for testing this module directly - requires mock config/logger)
if __name__ == '__main__':
    class MockConfig:
        # Define attributes that BasicStealthManager might access
        spoof_plugins_mimeTypes = True
        spoof_hardware_concurrency = 4
        spoof_device_memory = 8
        webgl_vendor = "Intel Inc."
        webgl_renderer = "Mesa Intel(R) UHD Graphics"
        permissions_default_granted = ["notifications"]
        # Add other config attributes as needed for testing specific scripts

    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARN: {msg}")
        def error(self, msg, exc_info=None): print(f"ERROR: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")

    mock_config = MockConfig()
    mock_logger = MockLogger()

    manager = BasicStealthManager(config=mock_config, logger=mock_logger)
    
    scripts_to_inject = manager.get_stealth_scripts()
    if scripts_to_inject:
        mock_logger.info(f"Generated {len(scripts_to_inject)} stealth scripts:")
        for i, script_info in enumerate(scripts_to_inject):
            mock_logger.info(f"--- Script {i+1}: {script_info['name']} ---")
            # mock_logger.info(script_info['source'][:200] + "...") # Print snippet
    else:
        mock_logger.info("No stealth scripts generated based on current mock config.")

    additional_options = manager.get_additional_chrome_options()
    mock_logger.info(f"Generated additional Chrome options: {additional_options}")

    # To test apply_js_stealth_to_driver, you'd need a mock driver object:
    # class MockDriver:
    #     def execute_cdp_cmd(self, cmd, params):
    #         mock_logger.info(f"Driver execute_cdp_cmd: {cmd} with source len {len(params.get('source',''))}")
    # mock_driver = MockDriver()
    # manager.apply_js_stealth_to_driver(mock_driver) 