#!/usr/bin/env python3
"""
Network Guard Module - Advanced Network-Level Stealth Protection
================================================================

Handles TLS fingerprint monitoring, proxy rotation, and network-level evasion
for the BrowserControL01 stealth web automation system.

Key Features:
- JA3/JA4 TLS fingerprint monitoring and verification
- Intelligent proxy rotation with reputation management
- Real-time network anomaly detection
- HTTP/2 consistency enforcement
- IP reputation and geolocation coherence
"""

import asyncio
import hashlib
import json
import time
import random
import logging
import socket
import ssl
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any
from urllib.parse import urlparse

import httpx
import requests
from fake_useragent import UserAgent


@dataclass
class NetworkConfig:
    """Network security configuration parameters"""
    
    # TLS fingerprint management
    expected_ja3_hashes: List[str] = field(default_factory=list)
    ja3_verification_endpoints: List[str] = field(default_factory=lambda: [
        "https://ja3er.com/json",
        "https://tls.browserleaks.com/json",
        "https://www.whatismybrowser.com/api/detect"
    ])
    
    # Proxy configuration
    proxy_rotation_interval: int = 300  # 5 minutes
    max_proxy_failures: int = 3
    proxy_timeout: int = 10
    
    # Network monitoring
    fingerprint_check_interval: int = 600  # 10 minutes
    anomaly_detection_threshold: float = 0.8
    network_delay_simulation: Tuple[float, float] = (0.1, 0.5)
    
    # Geographic coherence
    require_geo_coherence: bool = True
    allowed_countries: List[str] = field(default_factory=lambda: ["US", "CA", "GB", "DE", "FR"])


class TLSFingerprintAnalyzer:
    """Advanced TLS fingerprint analysis and verification system"""
    
    def __init__(self, config: NetworkConfig, logger: logging.Logger):
        self.config = config
        self.log = logger
        self.known_good_fingerprints = set()
        self.fingerprint_cache = {}
        self.last_check_time = 0
        
    async def verify_tls_fingerprint(self, target_url: str = None) -> Dict[str, Any]:
        """Verify current TLS fingerprint against known good patterns"""
        self.log.debug("Starting TLS fingerprint verification")
        
        verification_result = {
            'timestamp': time.time(),
            'status': 'unknown',
            'ja3_hash': None,
            'ja4_hash': None,
            'details': {},
            'recommendations': []
        }
        
        try:
            # Test multiple fingerprint detection services
            for endpoint in self.config.ja3_verification_endpoints:
                try:
                    fingerprint_data = await self._check_fingerprint_endpoint(endpoint)
                    if fingerprint_data:
                        verification_result['details'][endpoint] = fingerprint_data
                        
                        # Extract JA3 hash if available
                        if 'ja3' in fingerprint_data:
                            verification_result['ja3_hash'] = fingerprint_data['ja3']
                        
                        break  # Use first successful response
                        
                except Exception as e:
                    self.log.warning(f"Fingerprint check failed for {endpoint}: {e}")
                    continue
            
            # Analyze fingerprint consistency
            if verification_result['ja3_hash']:
                verification_result['status'] = self._analyze_fingerprint_safety(
                    verification_result['ja3_hash']
                )
            
            # Generate recommendations if needed
            if verification_result['status'] != 'safe':
                verification_result['recommendations'] = self._generate_fingerprint_recommendations(
                    verification_result
                )
            
            self.last_check_time = time.time()
            return verification_result
            
        except Exception as e:
            self.log.error(f"TLS fingerprint verification failed: {e}")
            verification_result['status'] = 'error'
            verification_result['error'] = str(e)
            return verification_result
    
    async def _check_fingerprint_endpoint(self, endpoint: str) -> Optional[Dict]:
        """Check TLS fingerprint against a specific detection service"""
        timeout = httpx.Timeout(10.0, connect=5.0)
        
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                response = await client.get(endpoint)
                
                if response.status_code == 200:
                    # Try to parse JSON response
                    try:
                        data = response.json()
                        return self._normalize_fingerprint_data(data, endpoint)
                    except json.JSONDecodeError:
                        # Some services return plain text
                        return self._parse_text_response(response.text, endpoint)
                        
            except httpx.TimeoutException:
                self.log.warning(f"Timeout checking fingerprint at {endpoint}")
            except Exception as e:
                self.log.warning(f"Error checking fingerprint at {endpoint}: {e}")
        
        return None
    
    def _normalize_fingerprint_data(self, data: Dict, source: str) -> Dict:
        """Normalize fingerprint data from different sources"""
        normalized = {
            'source': source,
            'timestamp': time.time()
        }
        
        # Handle different response formats
        if 'ja3' in data:
            normalized['ja3'] = data['ja3']
        elif 'ja3_hash' in data:
            normalized['ja3'] = data['ja3_hash']
        
        if 'user_agent' in data:
            normalized['user_agent'] = data['user_agent']
        
        if 'ip' in data:
            normalized['ip_address'] = data['ip']
        elif 'ip_address' in data:
            normalized['ip_address'] = data['ip_address']
        
        # Extract TLS version information
        if 'tls_version' in data:
            normalized['tls_version'] = data['tls_version']
        
        # Extract cipher information
        if 'cipher_suite' in data:
            normalized['cipher_suite'] = data['cipher_suite']
        
        return normalized
    
    def _parse_text_response(self, text: str, source: str) -> Dict:
        """Parse plain text fingerprint responses"""
        normalized = {
            'source': source,
            'timestamp': time.time(),
            'raw_response': text
        }
        
        # Look for JA3 hash patterns
        import re
        ja3_pattern = r'([a-f0-9]{32})'
        ja3_match = re.search(ja3_pattern, text.lower())
        if ja3_match:
            normalized['ja3'] = ja3_match.group(1)
        
        return normalized
    
    def _analyze_fingerprint_safety(self, ja3_hash: str) -> str:
        """Analyze if the TLS fingerprint appears safe"""
        # Check against known good fingerprints
        if ja3_hash in self.known_good_fingerprints:
            return 'safe'
        
        # Check if this is a common browser fingerprint
        common_browser_hashes = {
            # Chrome stable fingerprints
            '769,47-53-5-10-49171-49172-49161-49162-49191-49192-49171-49172-52393-52392-49199-49200-49195-49196-49197-49198-158-159-107-103-57-56-136-135-49167-49157-157-61-53-132-60-192-186-143-47,0-5-10-11-13-23-35-43-45-51-65281,23-24-25,0',
            # Firefox stable fingerprints  
            '771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-49161-49162-49191-49192-158-159-107-103-57-56-157-61-53-192-186-143-136-135-49167-49157-132-47,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-41,29-23-24,0'
        }
        
        if ja3_hash in common_browser_hashes:
            self.known_good_fingerprints.add(ja3_hash)
            return 'safe'
        
        # If fingerprint is new, mark as suspicious
        return 'suspicious'
    
    def _generate_fingerprint_recommendations(self, verification_result: Dict) -> List[str]:
        """Generate recommendations for improving fingerprint safety"""
        recommendations = []
        
        if verification_result['status'] == 'suspicious':
            recommendations.extend([
                "Consider updating Chrome to latest stable version",
                "Verify undetected-chromedriver version compatibility",
                "Check if proxy is terminating TLS connections",
                "Review Chrome startup arguments for TLS-affecting flags"
            ])
        
        if not verification_result.get('ja3_hash'):
            recommendations.append("Unable to detect JA3 fingerprint - check network connectivity")
        
        return recommendations


class ProxyRotationManager:
    """Intelligent proxy rotation with reputation management"""
    
    def __init__(self, config: NetworkConfig, logger: logging.Logger):
        self.config = config
        self.log = logger
        self.proxy_pool = []
        self.proxy_stats = {}
        self.current_proxy = None
        self.last_rotation = 0
        
    def add_proxy(self, proxy_url: str, proxy_type: str = "http", 
                  metadata: Dict = None) -> None:
        """Add a proxy to the rotation pool"""
        proxy_info = {
            'url': proxy_url,
            'type': proxy_type,
            'metadata': metadata or {},
            'added_time': time.time(),
            'success_count': 0,
            'failure_count': 0,
            'last_used': 0,
            'response_times': [],
            'status': 'active'
        }
        
        self.proxy_pool.append(proxy_info)
        self.proxy_stats[proxy_url] = proxy_info
        self.log.info(f"Added {proxy_type} proxy: {proxy_url}")
    
    def get_best_proxy(self) -> Optional[Dict]:
        """Select the best available proxy based on performance metrics"""
        if not self.proxy_pool:
            return None
        
        # Filter active proxies
        active_proxies = [p for p in self.proxy_pool if p['status'] == 'active']
        if not active_proxies:
            self.log.warning("No active proxies available")
            return None
        
        # Score proxies based on success rate and response time
        scored_proxies = []
        for proxy in active_proxies:
            score = self._calculate_proxy_score(proxy)
            scored_proxies.append((score, proxy))
        
        # Sort by score (higher is better)
        scored_proxies.sort(key=lambda x: x[0], reverse=True)
        
        # Select best proxy
        best_proxy = scored_proxies[0][1]
        self.current_proxy = best_proxy
        self.last_rotation = time.time()
        
        self.log.debug(f"Selected proxy: {best_proxy['url']} (score: {scored_proxies[0][0]:.2f})")
        return best_proxy
    
    def _calculate_proxy_score(self, proxy: Dict) -> float:
        """Calculate a performance score for a proxy"""
        total_requests = proxy['success_count'] + proxy['failure_count']
        
        if total_requests == 0:
            return 0.5  # Neutral score for untested proxies
        
        # Success rate component (0-1)
        success_rate = proxy['success_count'] / total_requests
        
        # Response time component (0-1, faster is better)
        avg_response_time = (
            sum(proxy['response_times']) / len(proxy['response_times']) 
            if proxy['response_times'] else 5.0
        )
        response_score = max(0, 1 - (avg_response_time / 10.0))  # Normalize to 10s max
        
        # Recency component (prefer recently successful proxies)
        time_since_use = time.time() - proxy['last_used']
        recency_score = max(0, 1 - (time_since_use / 3600))  # Decay over 1 hour
        
        # Weighted combination
        final_score = (
            success_rate * 0.5 +
            response_score * 0.3 +
            recency_score * 0.2
        )
        
        return final_score
    
    def record_proxy_result(self, proxy_url: str, success: bool, 
                           response_time: float = None) -> None:
        """Record the result of using a proxy"""
        if proxy_url not in self.proxy_stats:
            return
        
        proxy = self.proxy_stats[proxy_url]
        proxy['last_used'] = time.time()
        
        if success:
            proxy['success_count'] += 1
            if response_time:
                proxy['response_times'].append(response_time)
                # Keep only last 10 response times
                if len(proxy['response_times']) > 10:
                    proxy['response_times'] = proxy['response_times'][-10:]
        else:
            proxy['failure_count'] += 1
            
            # Disable proxy if too many failures
            if proxy['failure_count'] >= self.config.max_proxy_failures:
                proxy['status'] = 'disabled'
                self.log.warning(f"Disabled proxy due to failures: {proxy_url}")
    
    def should_rotate_proxy(self) -> bool:
        """Determine if it's time to rotate to a new proxy"""
        if not self.current_proxy:
            return True
        
        time_since_rotation = time.time() - self.last_rotation
        return time_since_rotation >= self.config.proxy_rotation_interval


class NetworkGuard:
    """Main network security orchestration system"""
    
    def __init__(self, config: NetworkConfig = None, logger: logging.Logger = None):
        self.config = config or NetworkConfig()
        self.log = logger or logging.getLogger(__name__)
        
        self.fingerprint_analyzer = TLSFingerprintAnalyzer(self.config, self.log)
        self.proxy_manager = ProxyRotationManager(self.config, self.log)
        
        self.last_security_check = 0
        self.security_status = {'fingerprint': 'unknown', 'network': 'unknown'}
        
    async def initialize_security_monitoring(self) -> Dict[str, Any]:
        """Initialize comprehensive network security monitoring"""
        self.log.info("Initializing network security monitoring")
        
        initialization_result = {
            'timestamp': time.time(),
            'status': 'success',
            'components': {},
            'warnings': []
        }
        
        try:
            # Verify TLS fingerprint
            fingerprint_result = await self.fingerprint_analyzer.verify_tls_fingerprint()
            initialization_result['components']['tls_fingerprint'] = fingerprint_result
            
            if fingerprint_result['status'] not in ['safe', 'unknown']:
                initialization_result['warnings'].append(
                    f"TLS fingerprint status: {fingerprint_result['status']}"
                )
            
            # Test proxy connectivity if configured
            if self.proxy_manager.proxy_pool:
                proxy_test = await self._test_proxy_connectivity()
                initialization_result['components']['proxy_test'] = proxy_test
                
                if not proxy_test['success']:
                    initialization_result['warnings'].append("Proxy connectivity issues detected")
            
            # Perform network consistency checks
            consistency_check = await self._verify_network_consistency()
            initialization_result['components']['network_consistency'] = consistency_check
            
            if not consistency_check['consistent']:
                initialization_result['warnings'].extend(consistency_check['issues'])
            
            self.last_security_check = time.time()
            
            if initialization_result['warnings']:
                initialization_result['status'] = 'warning'
                self.log.warning(f"Security initialization completed with warnings: {initialization_result['warnings']}")
            else:
                self.log.info("Network security monitoring initialized successfully")
            
            return initialization_result
            
        except Exception as e:
            self.log.error(f"Failed to initialize security monitoring: {e}")
            initialization_result['status'] = 'error'
            initialization_result['error'] = str(e)
            return initialization_result
    
    async def _test_proxy_connectivity(self) -> Dict[str, Any]:
        """Test connectivity and performance of configured proxies"""
        test_result = {
            'success': False,
            'tested_proxies': 0,
            'working_proxies': 0,
            'average_response_time': 0,
            'errors': []
        }
        
        test_url = "https://httpbin.org/ip"
        response_times = []
        
        for proxy in self.proxy_manager.proxy_pool:
            test_result['tested_proxies'] += 1
            
            try:
                start_time = time.time()
                
                # Test with httpx
                timeout = httpx.Timeout(self.config.proxy_timeout)
                async with httpx.AsyncClient(
                    proxies=proxy['url'], 
                    timeout=timeout,
                    follow_redirects=True
                ) as client:
                    response = await client.get(test_url)
                    
                    if response.status_code == 200:
                        response_time = time.time() - start_time
                        response_times.append(response_time)
                        test_result['working_proxies'] += 1
                        
                        self.proxy_manager.record_proxy_result(
                            proxy['url'], True, response_time
                        )
                    else:
                        self.proxy_manager.record_proxy_result(proxy['url'], False)
                        
            except Exception as e:
                test_result['errors'].append(f"{proxy['url']}: {str(e)}")
                self.proxy_manager.record_proxy_result(proxy['url'], False)
        
        if response_times:
            test_result['average_response_time'] = sum(response_times) / len(response_times)
            test_result['success'] = test_result['working_proxies'] > 0
        
        return test_result
    
    async def _verify_network_consistency(self) -> Dict[str, Any]:
        """Verify network configuration consistency"""
        consistency_result = {
            'consistent': True,
            'issues': [],
            'checks': {}
        }
        
        try:
            # Check HTTP/2 support
            http2_check = await self._check_http2_support()
            consistency_result['checks']['http2'] = http2_check
            
            if not http2_check['supported']:
                consistency_result['consistent'] = False
                consistency_result['issues'].append("HTTP/2 not supported - may indicate proxy issues")
            
            # Check geographic consistency
            geo_check = await self._check_geographic_consistency()
            consistency_result['checks']['geographic'] = geo_check
            
            if not geo_check['consistent']:
                consistency_result['consistent'] = False
                consistency_result['issues'].extend(geo_check['issues'])
            
            return consistency_result
            
        except Exception as e:
            consistency_result['consistent'] = False
            consistency_result['issues'].append(f"Network consistency check failed: {e}")
            return consistency_result
    
    async def _check_http2_support(self) -> Dict[str, Any]:
        """Verify HTTP/2 protocol support"""
        check_result = {
            'supported': False,
            'protocol_version': None,
            'error': None
        }
        
        try:
            async with httpx.AsyncClient(http2=True) as client:
                response = await client.get("https://http2.akamai.com/demo")
                
                # Check if HTTP/2 was actually used
                if hasattr(response, 'http_version'):
                    check_result['protocol_version'] = response.http_version
                    check_result['supported'] = response.http_version.startswith('HTTP/2')
                
        except Exception as e:
            check_result['error'] = str(e)
        
        return check_result
    
    async def _check_geographic_consistency(self) -> Dict[str, Any]:
        """Check geographic consistency between IP and browser locale"""
        geo_result = {
            'consistent': True,
            'issues': [],
            'detected_country': None,
            'expected_countries': self.config.allowed_countries
        }
        
        if not self.config.require_geo_coherence:
            geo_result['consistent'] = True
            return geo_result
        
        try:
            # Get IP geolocation
            async with httpx.AsyncClient() as client:
                response = await client.get("https://ipapi.co/json/")
                if response.status_code == 200:
                    geo_data = response.json()
                    detected_country = geo_data.get('country_code')
                    geo_result['detected_country'] = detected_country
                    
                    if detected_country not in self.config.allowed_countries:
                        geo_result['consistent'] = False
                        geo_result['issues'].append(
                            f"IP location ({detected_country}) not in allowed countries"
                        )
        
        except Exception as e:
            geo_result['issues'].append(f"Geographic check failed: {e}")
        
        return geo_result
    
    async def perform_security_audit(self) -> Dict[str, Any]:
        """Perform comprehensive security audit"""
        audit_result = {
            'timestamp': time.time(),
            'overall_status': 'unknown',
            'components': {},
            'recommendations': [],
            'risk_level': 'medium'
        }
        
        try:
            # TLS fingerprint check
            fingerprint_audit = await self.fingerprint_analyzer.verify_tls_fingerprint()
            audit_result['components']['tls_fingerprint'] = fingerprint_audit
            
            # Network consistency check
            network_audit = await self._verify_network_consistency()
            audit_result['components']['network_consistency'] = network_audit
            
            # Proxy performance audit
            if self.proxy_manager.proxy_pool:
                proxy_audit = await self._test_proxy_connectivity()
                audit_result['components']['proxy_performance'] = proxy_audit
            
            # Analyze overall security posture
            audit_result = self._analyze_security_posture(audit_result)
            
            self.log.info(f"Security audit completed - Status: {audit_result['overall_status']}")
            return audit_result
            
        except Exception as e:
            self.log.error(f"Security audit failed: {e}")
            audit_result['overall_status'] = 'error'
            audit_result['error'] = str(e)
            return audit_result
    
    def _analyze_security_posture(self, audit_result: Dict) -> Dict:
        """Analyze overall security posture and generate recommendations"""
        components = audit_result['components']
        issues = []
        recommendations = []
        
        # Analyze TLS fingerprint status
        fingerprint_status = components.get('tls_fingerprint', {}).get('status', 'unknown')
        if fingerprint_status == 'suspicious':
            issues.append('TLS fingerprint appears suspicious')
            recommendations.extend(components['tls_fingerprint'].get('recommendations', []))
        
        # Analyze network consistency
        network_consistent = components.get('network_consistency', {}).get('consistent', False)
        if not network_consistent:
            issues.extend(components['network_consistency'].get('issues', []))
            recommendations.append('Review network configuration and proxy settings')
        
        # Analyze proxy performance
        proxy_performance = components.get('proxy_performance', {})
        if proxy_performance and not proxy_performance.get('success', False):
            issues.append('Proxy connectivity issues detected')
            recommendations.append('Check proxy configuration and connectivity')
        
        # Determine overall status and risk level
        if not issues:
            audit_result['overall_status'] = 'secure'
            audit_result['risk_level'] = 'low'
        elif len(issues) == 1 and fingerprint_status == 'unknown':
            audit_result['overall_status'] = 'acceptable'
            audit_result['risk_level'] = 'medium'
        else:
            audit_result['overall_status'] = 'at_risk'
            audit_result['risk_level'] = 'high'
        
        audit_result['recommendations'] = recommendations
        return audit_result


# Utility functions for network monitoring
async def quick_fingerprint_check() -> Dict[str, Any]:
    """Quick TLS fingerprint verification for testing"""
    config = NetworkConfig()
    logger = logging.getLogger(__name__)
    
    analyzer = TLSFingerprintAnalyzer(config, logger)
    return await analyzer.verify_tls_fingerprint()


async def test_proxy_setup(proxy_urls: List[str]) -> Dict[str, Any]:
    """Test a list of proxy URLs for functionality"""
    config = NetworkConfig()
    logger = logging.getLogger(__name__)
    
    guard = NetworkGuard(config, logger)
    
    # Add proxies to manager
    for proxy_url in proxy_urls:
        guard.proxy_manager.add_proxy(proxy_url)
    
    # Test connectivity
    return await guard._test_proxy_connectivity()


if __name__ == "__main__":
    # Example usage and testing
    import asyncio
    
    async def main():
        logging.basicConfig(level=logging.INFO)
        
        # Quick fingerprint check
        print("🔍 Performing TLS fingerprint check...")
        fingerprint_result = await quick_fingerprint_check()
        print(f"Fingerprint Status: {fingerprint_result['status']}")
        
        if fingerprint_result.get('ja3_hash'):
            print(f"JA3 Hash: {fingerprint_result['ja3_hash']}")
        
        # Full security audit
        print("\n🛡️ Performing full security audit...")
        guard = NetworkGuard()
        audit_result = await guard.perform_security_audit()
        print(f"Overall Security Status: {audit_result['overall_status']}")
        print(f"Risk Level: {audit_result['risk_level']}")
        
        if audit_result['recommendations']:
            print("\nRecommendations:")
            for rec in audit_result['recommendations']:
                print(f"  • {rec}")
    
    asyncio.run(main()) 