#!/usr/bin/env python3
"""
Base Workflow for BrowserControL01 Automation
==============================================

Abstract base class for all automation workflows.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from core import SystemConfig, StealthBrowserManager, HumanBehaviorEngine, AdaptiveDOMInteractor
from utils.logger import get_logger, StealthLogger
from core.config import WorkflowConfig


class BaseWorkflow(ABC):
    """Abstract base class for automation workflows"""

    def __init__(self, config: SystemConfig = None, logger: StealthLogger = None,
                 init_components: bool = True):
        """Initialize workflow.

        Args:
            config: System configuration
            logger: Logger instance
            init_components: If True, initialize browser_manager, behavior, dom.
                           Subclasses can set False if they manage these differently.
        """
        self.config = config or SystemConfig()
        self.log = logger or StealthLogger()

        # Initialize core components only if requested
        # Subclasses like BaseSiteModule may handle this themselves
        if init_components:
            self.browser_manager = StealthBrowserManager(self.config, self.log)
            self.behavior = HumanBehaviorEngine(self.config, self.log)
            self.dom = AdaptiveDOMInteractor(self.config, self.log)
        else:
            self.browser_manager = None
            self.behavior = None
            self.dom = None

        self.start_time = None
        self.execution_data = {}
    
    @abstractmethod
    def execute(self, **params) -> Dict[str, Any]:
        """Execute the workflow with given parameters"""
        pass
    
    @abstractmethod
    def validate_params(self, **params) -> bool:
        """Validate workflow parameters"""
        pass
    
    def start_execution(self, **params) -> Dict[str, Any]:
        """Start workflow execution with common setup"""
        self.start_time = time.time()
        self.log.info(f"Starting {self.__class__.__name__} workflow")
        
        # Validate parameters
        if not self.validate_params(**params):
            return self._create_error_result("Parameter validation failed")
        
        # Initialize execution data
        self.execution_data = {
            'workflow_type': self.__class__.__name__,
            'start_time': self.start_time,
            'params': params,
            'success': False,
            'errors': [],
            'execution_time': 0
        }
        
        try:
            # Execute the workflow
            result = self.execute(**params)
            
            # Update execution data
            self.execution_data.update(result)
            self.execution_data['execution_time'] = time.time() - self.start_time
            
            if result.get('success'):
                self.log.info(f"Workflow completed successfully in {self.execution_data['execution_time']:.2f}s")
            else:
                self.log.error(f"Workflow failed: {', '.join(result.get('errors', []))}")
            
            return self.execution_data
            
        except Exception as e:
            self.execution_data['errors'].append(str(e))
            self.execution_data['execution_time'] = time.time() - self.start_time
            self.log.error(f"Workflow exception: {e}")
            return self.execution_data
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error result"""
        return {
            'success': False,
            'errors': [error_message],
            'execution_time': time.time() - (self.start_time or time.time())
        }
    
    def _create_success_result(self, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create standardized success result"""
        result = {
            'success': True,
            'errors': [],
            'execution_time': time.time() - (self.start_time or time.time())
        }
        
        if data:
            result.update(data)
        
        return result
    
    def navigate_with_retry(self, driver, url: str, max_retries: int = 3) -> bool:
        """Navigate to URL with retry logic"""
        for attempt in range(max_retries):
            try:
                driver.get(url)
                self.wait_for_page_ready(driver)
                return True
            except Exception as e:
                self.log.warning(f"Navigation attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    self.behavior.human_pause(1.0, 2.0)
        return False

    def wait_for_page_ready(self, driver, timeout: int = 10) -> bool:
        """Wait for page to be ready for interaction"""
        try:
            # Wait for document ready state
            start_time = time.time()
            while time.time() - start_time < timeout:
                ready_state = driver.execute_script("return document.readyState")
                if ready_state == "complete":
                    # Additional thinking time for human-like behavior
                    self.behavior.thinking_pause()
                    return True
                time.sleep(0.1)
            self.log.warning("Page did not reach ready state within timeout")
            return False
        except Exception as e:
            self.log.warning(f"Page ready check failed: {e}")
            return False
    
    def handle_workflow_error(self, error: Exception, context: str = "") -> None:
        """Handle workflow errors consistently"""
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.execution_data['errors'].append(error_msg)
        self.log.error(error_msg)
    
    def cleanup_resources(self) -> None:
        """Clean up workflow resources"""
        try:
            if self.browser_manager:
                self.browser_manager.cleanup()
        except Exception as e:
            self.log.warning(f"Resource cleanup error: {e}")


class WorkflowResult:
    """Standardized workflow result container"""
    
    def __init__(self, success: bool = False, data: Dict[str, Any] = None, 
                 errors: list = None, execution_time: float = 0):
        self.success = success
        self.data = data or {}
        self.errors = errors or []
        self.execution_time = execution_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'success': self.success,
            'data': self.data,
            'errors': self.errors,
            'execution_time': self.execution_time
        }
    
    def add_error(self, error: str) -> None:
        """Add an error to the result"""
        self.errors.append(error)
        self.success = False
    
    def set_data(self, key: str, value: Any) -> None:
        """Set data value"""
        self.data[key] = value 