"""
Service Container - Dependency Injection Container
"""

from typing import Dict, Any, Optional, Type, TypeVar, Callable
from functools import lru_cache
import threading

T = TypeVar('T')


class ServiceContainer:
    """
    Simple dependency injection container
    
    Manages service lifecycle and provides dependency resolution.
    Supports singleton and transient service registration.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register_singleton(
        self,
        service_name: str,
        instance: Any
    ) -> None:
        """
        Register a singleton service instance
        
        Args:
            service_name: Unique service identifier
            instance: Service instance to register
        """
        with self._lock:
            self._singletons[service_name] = instance
    
    def register_factory(
        self,
        service_name: str,
        factory: Callable[[], Any],
        singleton: bool = False
    ) -> None:
        """
        Register a service factory
        
        Args:
            service_name: Unique service identifier
            factory: Factory function that creates the service
            singleton: If True, factory result is cached
        """
        with self._lock:
            self._factories[service_name] = (factory, singleton)
    
    def get(self, service_name: str) -> Any:
        """
        Get a service instance
        
        Args:
            service_name: Service identifier
        
        Returns:
            Service instance
        
        Raises:
            ValueError: If service is not registered
        """
        # Check singletons first
        if service_name in self._singletons:
            return self._singletons[service_name]
        
        # Check factories
        if service_name in self._factories:
            factory, is_singleton = self._factories[service_name]
            
            if is_singleton:
                # Create and cache singleton
                if service_name not in self._singletons:
                    with self._lock:
                        if service_name not in self._singletons:
                            self._singletons[service_name] = factory()
                return self._singletons[service_name]
            else:
                # Create new instance each time
                return factory()
        
        raise ValueError(f"Service '{service_name}' is not registered")
    
    def has(self, service_name: str) -> bool:
        """Check if a service is registered"""
        return (
            service_name in self._singletons or
            service_name in self._factories
        )
    
    def clear(self) -> None:
        """Clear all registered services (useful for testing)"""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()


# Global container instance
_container: Optional[ServiceContainer] = None
_container_lock = threading.Lock()


def get_container() -> ServiceContainer:
    """Get global service container instance"""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = ServiceContainer()
    return _container


def reset_container() -> None:
    """Reset global container (useful for testing)"""
    global _container
    with _container_lock:
        _container = None

