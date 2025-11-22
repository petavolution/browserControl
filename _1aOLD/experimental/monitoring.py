#!/usr/bin/env python3
"""
Monitoring Module - Continuous Security Assessment & Detection Evasion
======================================================================

Provides real-time monitoring, self-assessment against detection services,
and adaptive security recommendations for the BrowserControL01 system.

Key Features:
- Continuous fingerprint monitoring against detection sites
- Behavioral pattern analysis and anomaly detection
- Real-time security dashboard and alerting
- Adaptive countermeasures and recommendations
- Historical trend analysis and reporting
"""

import asyncio
import time
import json
import logging
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
import httpx
from selenium import webdriver
from selenium.webdriver.common.by import By

from _1aOLD.experimental.network_guard import NetworkGuard, NetworkConfig


@dataclass
class MonitoringConfig:
    """Configuration for security monitoring system"""
    
    # Detection test sites
    detection_test_sites: List[str] = field(default_factory=lambda: [
        "https://bot.sannysoft.com/",
        "https://pixelscan.net/",
        "https://browserleaks.com/",
        "https://deviceinfo.me/",
        "https://fingerprintjs.com/demo/"
    ])
    
    # Monitoring intervals
    continuous_check_interval: int = 300  # 5 minutes
    deep_analysis_interval: int = 1800    # 30 minutes
    trend_analysis_interval: int = 3600   # 1 hour
    
    # Alert thresholds
    detection_risk_threshold: float = 0.7
    fingerprint_change_threshold: float = 0.3
    behavioral_anomaly_threshold: float = 0.8
    
    # Data retention
    max_history_records: int = 1000
    history_retention_days: int = 7
    
    # Reporting
    generate_reports: bool = True
    report_directory: Path = field(default_factory=lambda: Path("monitoring_reports"))


class DetectionTestEngine:
    """Engine for testing against bot detection services"""
    
    def __init__(self, config: MonitoringConfig, logger: logging.Logger):
        self.config = config
        self.log = logger
        self.test_results_cache = {}
        self.last_test_time = {}
        
    async def run_detection_tests(self, driver=None) -> Dict[str, Any]:
        """Run comprehensive detection tests against known services"""
        self.log.info("Starting detection test suite")
        
        test_results = {
            'timestamp': time.time(),
            'overall_risk_score': 0.0,
            'individual_tests': {},
            'detected_flags': [],
            'recommendations': [],
            'summary': {}
        }
        
        risk_scores = []
        detected_flags = []
        
        # Test each detection service
        for site_url in self.config.detection_test_sites:
            try:
                site_result = await self._test_detection_site(site_url, driver)
                test_results['individual_tests'][site_url] = site_result
                
                if site_result.get('risk_score') is not None:
                    risk_scores.append(site_result['risk_score'])
                
                if site_result.get('detected_flags'):
                    detected_flags.extend(site_result['detected_flags'])
                    
            except Exception as e:
                self.log.warning(f"Detection test failed for {site_url}: {e}")
                test_results['individual_tests'][site_url] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Calculate overall risk score
        if risk_scores:
            test_results['overall_risk_score'] = statistics.mean(risk_scores)
        
        # Deduplicate flags
        test_results['detected_flags'] = list(set(detected_flags))
        
        # Generate recommendations
        test_results['recommendations'] = self._generate_detection_recommendations(test_results)
        
        # Create summary
        test_results['summary'] = self._create_test_summary(test_results)
        
        self.log.info(f"Detection tests completed - Risk Score: {test_results['overall_risk_score']:.2f}")
        return test_results
    
    async def _test_detection_site(self, site_url: str, driver=None) -> Dict[str, Any]:
        """Test against a specific bot detection site"""
        site_result = {
            'url': site_url,
            'timestamp': time.time(),
            'status': 'unknown',
            'risk_score': 0.0,
            'detected_flags': [],
            'raw_data': {},
            'response_time': 0
        }
        
        start_time = time.time()
        
        try:
            if 'bot.sannysoft.com' in site_url:
                site_result.update(await self._test_sannysoft(site_url, driver))
            elif 'pixelscan.net' in site_url:
                site_result.update(await self._test_pixelscan(site_url, driver))
            elif 'browserleaks.com' in site_url:
                site_result.update(await self._test_browserleaks(site_url, driver))
            elif 'deviceinfo.me' in site_url:
                site_result.update(await self._test_deviceinfo(site_url, driver))
            elif 'fingerprintjs.com' in site_url:
                site_result.update(await self._test_fingerprintjs(site_url, driver))
            else:
                # Generic test
                site_result.update(await self._test_generic_site(site_url, driver))
            
            site_result['response_time'] = time.time() - start_time
            
        except Exception as e:
            site_result['status'] = 'error'
            site_result['error'] = str(e)
            site_result['response_time'] = time.time() - start_time
        
        return site_result
    
    async def _test_sannysoft(self, url: str, driver=None) -> Dict[str, Any]:
        """Test against bot.sannysoft.com detection service"""
        result = {'status': 'tested', 'detected_flags': [], 'risk_score': 0.0}
        
        if not driver:
            # HTTP-only test
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                if 'bot' in response.text.lower():
                    result['detected_flags'].append('http_bot_detection')
                    result['risk_score'] += 0.3
        else:
            # Full browser test
            driver.get(url)
            await asyncio.sleep(3)  # Wait for JS to execute
            
            # Check for common detection indicators
            detection_checks = [
                ("webdriver", "navigator.webdriver"),
                ("chrome_runtime", "window.chrome && window.chrome.runtime"),
                ("phantom", "window.callPhantom || window._phantom"),
                ("selenium", "window.__selenium_unwrapped || window.__webdriver_script_fn"),
            ]
            
            for flag_name, js_check in detection_checks:
                try:
                    detected = driver.execute_script(f"return !!({js_check});")
                    if detected:
                        result['detected_flags'].append(f"js_{flag_name}_detected")
                        result['risk_score'] += 0.2
                except Exception:
                    pass
            
            # Check page content for detection messages
            try:
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(keyword in page_text for keyword in ['detected', 'bot', 'automated']):
                    result['detected_flags'].append('content_detection_message')
                    result['risk_score'] += 0.4
            except Exception:
                pass
        
        result['status'] = 'completed'
        return result
    
    async def _test_pixelscan(self, url: str, driver=None) -> Dict[str, Any]:
        """Test against PixelScan fingerprinting service"""
        result = {'status': 'tested', 'detected_flags': [], 'risk_score': 0.0}
        
        if driver:
            try:
                driver.get(url)
                await asyncio.sleep(5)  # Wait for fingerprint collection
                
                # Look for automation detection indicators
                try:
                    automation_score = driver.execute_script("""
                        var score = 0;
                        if (navigator.webdriver) score += 0.3;
                        if (window.chrome && window.chrome.runtime) score += 0.2;
                        if (navigator.plugins.length === 0) score += 0.2;
                        if (navigator.languages.length === 0) score += 0.1;
                        return score;
                    """)
                    
                    result['risk_score'] = automation_score
                    if automation_score > 0.3:
                        result['detected_flags'].append('high_automation_score')
                        
                except Exception as e:
                    self.log.debug(f"PixelScan JS execution failed: {e}")
                
            except Exception as e:
                result['status'] = 'error'
                result['error'] = str(e)
        
        result['status'] = 'completed'
        return result
    
    async def _test_browserleaks(self, url: str, driver=None) -> Dict[str, Any]:
        """Test against BrowserLeaks fingerprinting service"""
        result = {'status': 'tested', 'detected_flags': [], 'risk_score': 0.0}
        
        # Test specific BrowserLeaks endpoints
        endpoints = [
            f"{url.rstrip('/')}/webgl",
            f"{url.rstrip('/')}/canvas",
            f"{url.rstrip('/')}/javascript"
        ]
        
        risk_accumulator = 0.0
        
        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(endpoint, timeout=10)
                    
                    # Analyze response for automation indicators
                    content = response.text.lower()
                    
                    # Check for common automation fingerprints
                    automation_indicators = [
                        'webdriver', 'selenium', 'phantomjs', 'chromedriver',
                        'automation', 'headless', 'bot'
                    ]
                    
                    found_indicators = [ind for ind in automation_indicators if ind in content]
                    if found_indicators:
                        result['detected_flags'].extend([f"content_{ind}" for ind in found_indicators])
                        risk_accumulator += len(found_indicators) * 0.1
                        
            except Exception as e:
                self.log.debug(f"BrowserLeaks endpoint test failed for {endpoint}: {e}")
        
        result['risk_score'] = min(risk_accumulator, 1.0)
        result['status'] = 'completed'
        return result
    
    async def _test_deviceinfo(self, url: str, driver=None) -> Dict[str, Any]:
        """Test against DeviceInfo.me"""
        result = {'status': 'tested', 'detected_flags': [], 'risk_score': 0.0}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                
                # Basic check for automation detection
                if response.status_code == 403:
                    result['detected_flags'].append('blocked_by_service')
                    result['risk_score'] = 0.8
                elif 'bot' in response.text.lower():
                    result['detected_flags'].append('bot_detected_in_response')
                    result['risk_score'] = 0.6
                    
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        result['status'] = 'completed'
        return result
    
    async def _test_fingerprintjs(self, url: str, driver=None) -> Dict[str, Any]:
        """Test against FingerprintJS demo"""
        result = {'status': 'tested', 'detected_flags': [], 'risk_score': 0.0}
        
        if driver:
            try:
                driver.get(url)
                await asyncio.sleep(4)  # Wait for fingerprint calculation
                
                # Check for bot probability score
                try:
                    bot_probability = driver.execute_script("""
                        // Check if FingerprintJS detected automation
                        var fpElements = document.querySelectorAll('[data-testid*="bot"], [class*="bot"]');
                        var botScore = 0;
                        
                        fpElements.forEach(function(el) {
                            var text = el.textContent.toLowerCase();
                            if (text.includes('high') || text.includes('detected')) {
                                botScore = 0.8;
                            } else if (text.includes('medium') || text.includes('likely')) {
                                botScore = 0.5;
                            }
                        });
                        
                        return botScore;
                    """)
                    
                    if bot_probability > 0:
                        result['risk_score'] = bot_probability
                        result['detected_flags'].append(f"fingerprintjs_bot_score_{bot_probability}")
                        
                except Exception as e:
                    self.log.debug(f"FingerprintJS analysis failed: {e}")
                
            except Exception as e:
                result['status'] = 'error'
                result['error'] = str(e)
        
        result['status'] = 'completed'
        return result
    
    async def _test_generic_site(self, url: str, driver=None) -> Dict[str, Any]:
        """Generic test for unknown detection sites"""
        result = {'status': 'tested', 'detected_flags': [], 'risk_score': 0.0}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10)
                
                # Basic heuristic checks
                content = response.text.lower()
                
                # Check for blocking or detection
                if response.status_code in [403, 429]:
                    result['detected_flags'].append('http_blocked')
                    result['risk_score'] = 0.7
                elif any(word in content for word in ['blocked', 'detected', 'bot', 'automation']):
                    result['detected_flags'].append('content_detection')
                    result['risk_score'] = 0.5
                    
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        result['status'] = 'completed'
        return result
    
    def _generate_detection_recommendations(self, test_results: Dict) -> List[str]:
        """Generate recommendations based on detection test results"""
        recommendations = []
        
        overall_risk = test_results['overall_risk_score']
        detected_flags = test_results['detected_flags']
        
        if overall_risk > self.config.detection_risk_threshold:
            recommendations.append("HIGH RISK: Multiple detection signals found - review stealth configuration")
        
        # Specific recommendations based on detected flags
        if any('webdriver' in flag for flag in detected_flags):
            recommendations.append("navigator.webdriver property detected - verify UC patches")
        
        if any('chrome_runtime' in flag for flag in detected_flags):
            recommendations.append("Chrome runtime detected - check stealth script injection")
        
        if any('blocked' in flag for flag in detected_flags):
            recommendations.append("HTTP blocking detected - consider proxy rotation")
        
        if any('fingerprint' in flag for flag in detected_flags):
            recommendations.append("Fingerprint-based detection - review WebGL/Canvas spoofing")
        
        return recommendations
    
    def _create_test_summary(self, test_results: Dict) -> Dict[str, Any]:
        """Create a summary of test results"""
        summary = {
            'total_tests': len(test_results['individual_tests']),
            'successful_tests': 0,
            'failed_tests': 0,
            'high_risk_tests': 0,
            'detected_flags_count': len(test_results['detected_flags']),
            'overall_assessment': 'unknown'
        }
        
        for test_url, test_data in test_results['individual_tests'].items():
            if test_data.get('status') == 'completed':
                summary['successful_tests'] += 1
                if test_data.get('risk_score', 0) > self.config.detection_risk_threshold:
                    summary['high_risk_tests'] += 1
            else:
                summary['failed_tests'] += 1
        
        # Overall assessment
        if test_results['overall_risk_score'] < 0.3:
            summary['overall_assessment'] = 'low_risk'
        elif test_results['overall_risk_score'] < 0.7:
            summary['overall_assessment'] = 'medium_risk'
        else:
            summary['overall_assessment'] = 'high_risk'
        
        return summary


class SecurityDashboard:
    """Real-time security monitoring dashboard"""
    
    def __init__(self, config: MonitoringConfig, logger: logging.Logger):
        self.config = config
        self.log = logger
        self.monitoring_history = []
        self.alert_callbacks = []
        
    def add_alert_callback(self, callback: Callable[[Dict], None]) -> None:
        """Add a callback function for security alerts"""
        self.alert_callbacks.append(callback)
    
    def record_monitoring_data(self, data: Dict[str, Any]) -> None:
        """Record new monitoring data point"""
        data['recorded_at'] = time.time()
        self.monitoring_history.append(data)
        
        # Maintain history size limit
        if len(self.monitoring_history) > self.config.max_history_records:
            self.monitoring_history = self.monitoring_history[-self.config.max_history_records:]
        
        # Check for alerts
        self._check_for_alerts(data)
    
    def _check_for_alerts(self, data: Dict[str, Any]) -> None:
        """Check if monitoring data triggers any alerts"""
        alerts = []
        
        # Risk threshold alert
        if data.get('overall_risk_score', 0) > self.config.detection_risk_threshold:
            alerts.append({
                'type': 'high_risk_detected',
                'severity': 'high',
                'message': f"High detection risk: {data['overall_risk_score']:.2f}",
                'data': data
            })
        
        # New detection flags alert
        if data.get('detected_flags'):
            alerts.append({
                'type': 'detection_flags',
                'severity': 'medium',
                'message': f"Detection flags found: {', '.join(data['detected_flags'])}",
                'data': data
            })
        
        # Fingerprint change alert
        if self._detect_fingerprint_changes(data):
            alerts.append({
                'type': 'fingerprint_change',
                'severity': 'medium',
                'message': "Significant fingerprint changes detected",
                'data': data
            })
        
        # Send alerts to callbacks
        for alert in alerts:
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.log.error(f"Alert callback failed: {e}")
    
    def _detect_fingerprint_changes(self, current_data: Dict) -> bool:
        """Detect significant changes in fingerprint data"""
        if len(self.monitoring_history) < 2:
            return False
        
        previous_data = self.monitoring_history[-2]
        
        # Compare fingerprint-related data
        current_fingerprint = current_data.get('fingerprint_data', {})
        previous_fingerprint = previous_data.get('fingerprint_data', {})
        
        # Simple change detection (can be enhanced)
        changes = 0
        total_fields = 0
        
        for key in set(current_fingerprint.keys()) | set(previous_fingerprint.keys()):
            total_fields += 1
            if current_fingerprint.get(key) != previous_fingerprint.get(key):
                changes += 1
        
        if total_fields > 0:
            change_ratio = changes / total_fields
            return change_ratio > self.config.fingerprint_change_threshold
        
        return False
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current security status summary"""
        if not self.monitoring_history:
            return {'status': 'no_data', 'last_update': None}
        
        latest_data = self.monitoring_history[-1]
        
        status = {
            'status': 'operational',
            'last_update': latest_data.get('recorded_at'),
            'risk_score': latest_data.get('overall_risk_score', 0),
            'active_flags': latest_data.get('detected_flags', []),
            'trend': self._calculate_risk_trend(),
            'uptime': self._calculate_uptime(),
            'total_tests': len(self.monitoring_history)
        }
        
        # Determine status level
        risk_score = status['risk_score']
        if risk_score > 0.8:
            status['status'] = 'critical'
        elif risk_score > 0.6:
            status['status'] = 'warning'
        elif risk_score > 0.3:
            status['status'] = 'caution'
        else:
            status['status'] = 'operational'
        
        return status
    
    def _calculate_risk_trend(self) -> str:
        """Calculate risk trend over recent history"""
        if len(self.monitoring_history) < 3:
            return 'insufficient_data'
        
        recent_scores = [
            data.get('overall_risk_score', 0) 
            for data in self.monitoring_history[-5:]
        ]
        
        if len(recent_scores) >= 2:
            trend = recent_scores[-1] - recent_scores[0]
            if trend > 0.1:
                return 'increasing'
            elif trend < -0.1:
                return 'decreasing'
            else:
                return 'stable'
        
        return 'stable'
    
    def _calculate_uptime(self) -> float:
        """Calculate system uptime percentage"""
        if not self.monitoring_history:
            return 0.0
        
        successful_tests = sum(
            1 for data in self.monitoring_history 
            if data.get('status') != 'error'
        )
        
        return (successful_tests / len(self.monitoring_history)) * 100
    
    def generate_report(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        cutoff_time = time.time() - (time_range_hours * 3600)
        relevant_data = [
            data for data in self.monitoring_history 
            if data.get('recorded_at', 0) > cutoff_time
        ]
        
        if not relevant_data:
            return {'error': 'No data available for requested time range'}
        
        report = {
            'report_period': f"{time_range_hours} hours",
            'generated_at': time.time(),
            'summary': {
                'total_tests': len(relevant_data),
                'average_risk_score': statistics.mean([
                    data.get('overall_risk_score', 0) for data in relevant_data
                ]),
                'max_risk_score': max([
                    data.get('overall_risk_score', 0) for data in relevant_data
                ]),
                'unique_flags': len(set().union(*[
                    data.get('detected_flags', []) for data in relevant_data
                ])),
                'uptime_percentage': len([
                    d for d in relevant_data if d.get('status') != 'error'
                ]) / len(relevant_data) * 100
            },
            'trends': {
                'risk_trend': self._calculate_risk_trend(),
                'hourly_averages': self._calculate_hourly_averages(relevant_data)
            },
            'alerts': [
                data for data in relevant_data 
                if data.get('overall_risk_score', 0) > self.config.detection_risk_threshold
            ],
            'recommendations': self._generate_report_recommendations(relevant_data)
        }
        
        return report
    
    def _calculate_hourly_averages(self, data_points: List[Dict]) -> Dict[int, float]:
        """Calculate hourly average risk scores"""
        hourly_data = {}
        
        for data in data_points:
            timestamp = data.get('recorded_at', 0)
            hour = int((timestamp % 86400) // 3600)  # Hour of day (0-23)
            risk_score = data.get('overall_risk_score', 0)
            
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(risk_score)
        
        return {
            hour: statistics.mean(scores) 
            for hour, scores in hourly_data.items()
        }
    
    def _generate_report_recommendations(self, data_points: List[Dict]) -> List[str]:
        """Generate recommendations based on historical data"""
        recommendations = []
        
        avg_risk = statistics.mean([d.get('overall_risk_score', 0) for d in data_points])
        
        if avg_risk > 0.5:
            recommendations.append("Consider reviewing and updating stealth configuration")
        
        # Check for recurring flags
        all_flags = []
        for data in data_points:
            all_flags.extend(data.get('detected_flags', []))
        
        flag_counts = {}
        for flag in all_flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
        
        recurring_flags = [flag for flag, count in flag_counts.items() if count > len(data_points) * 0.3]
        
        if recurring_flags:
            recommendations.append(f"Address recurring detection flags: {', '.join(recurring_flags)}")
        
        return recommendations


class ContinuousMonitor:
    """Main continuous monitoring orchestrator"""
    
    def __init__(self, config: MonitoringConfig = None, network_guard: NetworkGuard = None):
        self.config = config or MonitoringConfig()
        self.log = logging.getLogger(__name__)
        
        self.network_guard = network_guard or NetworkGuard()
        self.detection_engine = DetectionTestEngine(self.config, self.log)
        self.dashboard = SecurityDashboard(self.config, self.log)
        
        self.monitoring_active = False
        self.monitoring_task = None
    
    async def start_monitoring(self) -> None:
        """Start continuous security monitoring"""
        if self.monitoring_active:
            self.log.warning("Monitoring already active")
            return
        
        self.log.info("Starting continuous security monitoring")
        self.monitoring_active = True
        
        # Set up alert callback
        self.dashboard.add_alert_callback(self._handle_security_alert)
        
        # Start monitoring loop
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self) -> None:
        """Stop continuous monitoring"""
        self.log.info("Stopping continuous security monitoring")
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        last_deep_analysis = 0
        last_trend_analysis = 0
        
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                # Perform quick security checks
                await self._perform_quick_check()
                
                # Perform deep analysis if needed
                if current_time - last_deep_analysis > self.config.deep_analysis_interval:
                    await self._perform_deep_analysis()
                    last_deep_analysis = current_time
                
                # Perform trend analysis if needed
                if current_time - last_trend_analysis > self.config.trend_analysis_interval:
                    await self._perform_trend_analysis()
                    last_trend_analysis = current_time
                
                # Wait for next check
                await asyncio.sleep(self.config.continuous_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _perform_quick_check(self) -> None:
        """Perform quick security check"""
        try:
            # Quick network fingerprint check
            network_status = await self.network_guard.fingerprint_analyzer.verify_tls_fingerprint()
            
            monitoring_data = {
                'check_type': 'quick',
                'timestamp': time.time(),
                'network_status': network_status,
                'overall_risk_score': 0.2 if network_status['status'] == 'suspicious' else 0.0,
                'detected_flags': [],
                'status': 'completed'
            }
            
            if network_status['status'] == 'suspicious':
                monitoring_data['detected_flags'].append('suspicious_tls_fingerprint')
            
            self.dashboard.record_monitoring_data(monitoring_data)
            
        except Exception as e:
            self.log.error(f"Quick check failed: {e}")
    
    async def _perform_deep_analysis(self) -> None:
        """Perform comprehensive deep analysis"""
        try:
            self.log.info("Performing deep security analysis")
            
            # Run full detection test suite
            detection_results = await self.detection_engine.run_detection_tests()
            
            # Perform network security audit
            network_audit = await self.network_guard.perform_security_audit()
            
            # Combine results
            monitoring_data = {
                'check_type': 'deep',
                'timestamp': time.time(),
                'detection_results': detection_results,
                'network_audit': network_audit,
                'overall_risk_score': max(
                    detection_results.get('overall_risk_score', 0),
                    0.5 if network_audit.get('risk_level') == 'high' else 0.0
                ),
                'detected_flags': detection_results.get('detected_flags', []),
                'status': 'completed'
            }
            
            self.dashboard.record_monitoring_data(monitoring_data)
            
        except Exception as e:
            self.log.error(f"Deep analysis failed: {e}")
    
    async def _perform_trend_analysis(self) -> None:
        """Perform trend analysis and generate reports"""
        try:
            self.log.info("Performing trend analysis")
            
            # Generate report
            report = self.dashboard.generate_report(time_range_hours=24)
            
            # Save report if configured
            if self.config.generate_reports:
                await self._save_report(report)
            
        except Exception as e:
            self.log.error(f"Trend analysis failed: {e}")
    
    async def _save_report(self, report: Dict) -> None:
        """Save monitoring report to file"""
        try:
            self.config.report_directory.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.config.report_directory / f"security_report_{timestamp}.json"
            
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.log.info(f"Security report saved: {report_file}")
            
        except Exception as e:
            self.log.error(f"Failed to save report: {e}")
    
    def _handle_security_alert(self, alert: Dict) -> None:
        """Handle security alerts"""
        severity = alert.get('severity', 'unknown')
        message = alert.get('message', 'Unknown alert')
        
        if severity == 'high':
            self.log.error(f"SECURITY ALERT: {message}")
        elif severity == 'medium':
            self.log.warning(f"Security Warning: {message}")
        else:
            self.log.info(f"Security Notice: {message}")
    
    def get_dashboard_status(self) -> Dict[str, Any]:
        """Get current dashboard status"""
        return self.dashboard.get_current_status()


# Utility functions
async def run_quick_security_scan() -> Dict[str, Any]:
    """Run a quick security scan for immediate assessment"""
    config = MonitoringConfig()
    logger = logging.getLogger(__name__)
    
    engine = DetectionTestEngine(config, logger)
    return await engine.run_detection_tests()


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        logging.basicConfig(level=logging.INFO)
        
        print("🔍 Starting quick security scan...")
        scan_result = await run_quick_security_scan()
        
        print(f"Overall Risk Score: {scan_result['overall_risk_score']:.2f}")
        print(f"Detected Flags: {scan_result['detected_flags']}")
        
        if scan_result['recommendations']:
            print("\nRecommendations:")
            for rec in scan_result['recommendations']:
                print(f"  • {rec}")
    
    asyncio.run(main()) 