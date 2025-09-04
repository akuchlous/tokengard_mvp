"""
Proxy Logger and Metrics

FLOW OVERVIEW
- log_request(request_data, client_ip, user_agent, request_id)
  • Create a correlation id (if missing) and log basic request metadata.

- log_response(request_id, response_data, status_code, processing_time_ms, ...)
  • Persist a `ProxyLog` row (with api_key if validated or raw value if not).
  • Compute tokens/cost (via token_counter) and include cache savings when applicable.
  • Emit readable log lines and structured metrics.

- log_metrics(request_id, metrics)
  • Emit detailed, structured metrics for observability.

- MetricsCollector
  • record_request(endpoint, status, latency, client_ip, token_info, cost_info)
  • get_metrics(minutes): aggregate windowed metrics with cache hit and cost savings rates.
"""

import time
import uuid
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from flask import request, current_app
from ..models import ProxyLog, db
from .prom_metrics import observe_request


class ProxyLogger:
    """Main proxy logger class."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def log_request(self, request_data: Dict[str, Any], client_ip: str = None, 
                   user_agent: str = None, request_id: str = None) -> str:
        """
        Log an incoming request.
        
        Args:
            request_data: Request data dictionary
            client_ip: Client IP address
            user_agent: User agent string
            request_id: Unique request ID (generated if not provided)
            
        Returns:
            Request ID for correlation
        """
        if not request_id:
            request_id = str(uuid.uuid4())
        
        try:
            # Extract metadata
            if not client_ip:
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                              request.environ.get('REMOTE_ADDR', 'unknown'))
            
            if not user_agent:
                user_agent = request.headers.get('User-Agent', 'unknown')
            
            # Log request details
            self.logger.info(f"Request {request_id} from {client_ip}: {request_data.get('api_key', 'no-key')[:10]}...")
            
            return request_id
            
        except Exception as e:
            self.logger.error(f"Error logging request: {str(e)}")
            return request_id
    
    def log_response(self, request_id: str, response_data: Dict[str, Any], 
                    status_code: int, processing_time_ms: int, 
                    api_key_record=None, client_ip: str = None, 
                    user_agent: str = None, data: Dict[str, Any] = None,
                    model: str = 'default', from_cache: bool = False,
                    token_info: Dict[str, Any] = None, cost_info: Dict[str, Any] = None) -> None:
        """
        Log a response and create database entry.
        
        Args:
            request_id: Request ID for correlation
            response_data: Response data dictionary
            status_code: HTTP status code
            processing_time_ms: Processing time in milliseconds
            api_key_record: API key record (if valid)
            client_ip: Client IP address
            user_agent: User agent string
            data: Original request data
            model: Model used for the request
            from_cache: Whether response came from cache
        """
        try:
            # Extract metadata
            if not client_ip:
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                              request.environ.get('REMOTE_ADDR', 'unknown'))
            
            if not user_agent:
                user_agent = request.headers.get('User-Agent', 'unknown')
            
            # Determine response status
            response_status = 'key_error'  # Default
            if status_code == 200:
                response_status = response_data.get('status', 'key_pass')
            elif status_code >= 400 and status_code < 500:
                response_status = response_data.get('status', 'key_error')
            elif status_code >= 500:
                response_status = 'server_error'
            
            # Create log entry
            if api_key_record:
                # Valid key record exists
                log_entry = ProxyLog.create_log(
                    api_key=api_key_record,
                    request_body=json.dumps(data) if data else None,
                    response_status=response_status,
                    response_body=json.dumps(response_data) if response_data else None,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    request_id=request_id,
                    processing_time_ms=processing_time_ms
                )
            else:
                # No key record found, but we want to log the attempt
                attempted_key = data.get('api_key', '')[:64] if data else ''
                log_entry = ProxyLog(
                    api_key_id=None,  # No valid key record
                    api_key_value=attempted_key,
                    request_body=json.dumps(data) if data else None,
                    response_status=response_status,
                    response_body=json.dumps(response_data) if response_data else None,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    request_id=request_id,
                    processing_time_ms=processing_time_ms
                )
                db.session.add(log_entry)
            
            # Commit the log entry
            db.session.commit()
            
            # Calculate token counts and cost metrics (prefer provided tiktoken-based data)
            if token_info is None:
                token_info = {}
            if cost_info is None:
                cost_info = {}
            
            # Log response details with token and cost information
            log_message = f"Response {request_id}: {status_code} - {response_status} ({processing_time_ms}ms)"
            if token_info:
                log_message += f" | Tokens: {token_info.get('input_tokens', 0)}→{token_info.get('output_tokens', 0)}"
            if cost_info:
                if cost_info.get('cache_hit'):
                    log_message += f" | Cache hit: ${cost_info.get('cost_saved', 0.0):.6f} saved"
                elif 'actual_cost' in cost_info:
                    log_message += f" | Cost: ${cost_info['actual_cost']:.6f}"
            
            self.logger.info(log_message)
            
            # Log detailed metrics
            if token_info or cost_info:
                self.log_metrics(request_id, {
                    'tokens': token_info,
                    'cost': cost_info,
                    'model': model,
                    'from_cache': from_cache
                })
            # Prometheus request metrics
            try:
                observe_request('/api/proxy', status_code, processing_time_ms / 1000.0)
            except Exception:
                pass
            
        except Exception as e:
            self.logger.error(f"Error logging response: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
    
    def log_metrics(self, request_id: str, metrics: Dict[str, Any]) -> None:
        """
        Log custom metrics for a request.
        
        Args:
            request_id: Request ID for correlation
            metrics: Metrics dictionary
        """
        try:
            self.logger.info(f"Metrics {request_id}: {json.dumps(metrics)}")
        except Exception as e:
            self.logger.error(f"Error logging metrics: {str(e)}")
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], 
                          client_ip: str = None) -> None:
        """
        Log security-related events.
        
        Args:
            event_type: Type of security event
            details: Event details
            client_ip: Client IP address
        """
        try:
            if not client_ip:
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                              request.environ.get('REMOTE_ADDR', 'unknown'))
            
            self.logger.warning(f"Security event [{event_type}] from {client_ip}: {json.dumps(details)}")
        except Exception as e:
            self.logger.error(f"Error logging security event: {str(e)}")


class MetricsCollector:
    """Collects and aggregates metrics for the proxy."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._metrics = {}
    
    def record_request(self, endpoint: str, status_code: int, 
                      processing_time_ms: int, client_ip: str = None,
                      token_info: Dict[str, Any] = None, cost_info: Dict[str, Any] = None) -> None:
        """
        Record a request metric.
        
        Args:
            endpoint: API endpoint
            status_code: HTTP status code
            processing_time_ms: Processing time in milliseconds
            client_ip: Client IP address
            token_info: Token count information
            cost_info: Cost information
        """
        try:
            timestamp = int(time.time())
            minute_key = f"{timestamp // 60}"
            
            if minute_key not in self._metrics:
                self._metrics[minute_key] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'total_processing_time': 0,
                    'endpoints': {},
                    'status_codes': {},
                    'client_ips': {},
                    'total_tokens': 0,
                    'total_cost': 0.0,
                    'total_cost_saved': 0.0,
                    'cache_hits': 0,
                    'llm_calls': 0
                }
            
            metrics = self._metrics[minute_key]
            metrics['total_requests'] += 1
            metrics['total_processing_time'] += processing_time_ms
            
            # Endpoint metrics
            if endpoint not in metrics['endpoints']:
                metrics['endpoints'][endpoint] = 0
            metrics['endpoints'][endpoint] += 1
            
            # Status code metrics
            if status_code not in metrics['status_codes']:
                metrics['status_codes'][status_code] = 0
            metrics['status_codes'][status_code] += 1
            
            # Client IP metrics
            if client_ip:
                if client_ip not in metrics['client_ips']:
                    metrics['client_ips'][client_ip] = 0
                metrics['client_ips'][client_ip] += 1
            
            # Success/failure metrics
            if 200 <= status_code < 300:
                metrics['successful_requests'] += 1
            else:
                metrics['failed_requests'] += 1
            
            # Token and cost metrics
            if token_info:
                metrics['total_tokens'] += token_info.get('input_tokens', 0) + token_info.get('output_tokens', 0)
            
            if cost_info:
                if cost_info.get('cache_hit'):
                    metrics['cache_hits'] += 1
                    metrics['total_cost_saved'] += cost_info.get('cost_saved', 0.0)
                else:
                    metrics['llm_calls'] += 1
                    metrics['total_cost'] += cost_info.get('actual_cost', 0.0)
            
            # Clean old metrics (older than 1 hour)
            self._cleanup_old_metrics()
            
        except Exception as e:
            self.logger.error(f"Error recording request metric: {str(e)}")
    
    def get_metrics(self, minutes: int = 60) -> Dict[str, Any]:
        """
        Get aggregated metrics for the last N minutes.
        
        Args:
            minutes: Number of minutes to aggregate
            
        Returns:
            Aggregated metrics dictionary
        """
        try:
            current_time = int(time.time())
            cutoff_time = current_time - (minutes * 60)
            
            aggregated = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'total_processing_time': 0,
                'avg_processing_time': 0,
                'endpoints': {},
                'status_codes': {},
                'client_ips': {},
                'total_tokens': 0,
                'total_cost': 0.0,
                'total_cost_saved': 0.0,
                'cache_hits': 0,
                'llm_calls': 0,
                'cache_hit_rate': 0.0,
                'cost_savings_rate': 0.0,
                'cache': {
                    'lookups': 0,
                    'hits': 0,
                    'avg_lookup_ms': 0.0,
                    'best_score_max': 0.0,
                    'per_user': {}
                },
                'time_range': {
                    'start': cutoff_time,
                    'end': current_time,
                    'minutes': minutes
                }
            }
            
            for minute_key, metrics in self._metrics.items():
                minute_timestamp = int(minute_key) * 60
                if minute_timestamp >= cutoff_time:
                    aggregated['total_requests'] += metrics['total_requests']
                    aggregated['successful_requests'] += metrics['successful_requests']
                    aggregated['failed_requests'] += metrics['failed_requests']
                    aggregated['total_processing_time'] += metrics['total_processing_time']
                    aggregated['total_tokens'] += metrics['total_tokens']
                    aggregated['total_cost'] += metrics['total_cost']
                    aggregated['total_cost_saved'] += metrics['total_cost_saved']
                    aggregated['cache_hits'] += metrics['cache_hits']
                    aggregated['llm_calls'] += metrics['llm_calls']
                    # Cache sub-aggregation
                    cache_m = metrics.get('cache', {})
                    aggregated['cache']['lookups'] += cache_m.get('lookups', 0)
                    aggregated['cache']['hits'] += cache_m.get('hits', 0)
                    aggregated['cache']['avg_lookup_ms'] += cache_m.get('total_lookup_ms', 0)
                    aggregated['cache']['best_score_max'] = max(
                        aggregated['cache']['best_score_max'], cache_m.get('best_score_max', 0.0)
                    )
                    for user_hash, u in cache_m.get('per_user', {}).items():
                        if user_hash not in aggregated['cache']['per_user']:
                            aggregated['cache']['per_user'][user_hash] = {'lookups': 0, 'hits': 0}
                        aggregated['cache']['per_user'][user_hash]['lookups'] += u.get('lookups', 0)
                        aggregated['cache']['per_user'][user_hash]['hits'] += u.get('hits', 0)
                    
                    # Aggregate endpoints
                    for endpoint, count in metrics['endpoints'].items():
                        if endpoint not in aggregated['endpoints']:
                            aggregated['endpoints'][endpoint] = 0
                        aggregated['endpoints'][endpoint] += count
                    
                    # Aggregate status codes
                    for status_code, count in metrics['status_codes'].items():
                        if status_code not in aggregated['status_codes']:
                            aggregated['status_codes'][status_code] = 0
                        aggregated['status_codes'][status_code] += count
                    
                    # Aggregate client IPs
                    for client_ip, count in metrics['client_ips'].items():
                        if client_ip not in aggregated['client_ips']:
                            aggregated['client_ips'][client_ip] = 0
                        aggregated['client_ips'][client_ip] += count
            
            # Calculate average processing time and rates
            if aggregated['total_requests'] > 0:
                aggregated['avg_processing_time'] = aggregated['total_processing_time'] / aggregated['total_requests']
            
            # Calculate cache hit rate
            total_successful_requests = aggregated['cache_hits'] + aggregated['llm_calls']
            if total_successful_requests > 0:
                aggregated['cache_hit_rate'] = round((aggregated['cache_hits'] / total_successful_requests) * 100, 2)
            
            # Calculate cost savings rate
            total_potential_cost = aggregated['total_cost'] + aggregated['total_cost_saved']
            if total_potential_cost > 0:
                aggregated['cost_savings_rate'] = round((aggregated['total_cost_saved'] / total_potential_cost) * 100, 2)
            # Finalize cache avg lookup ms
            if aggregated['cache']['lookups'] > 0:
                aggregated['cache']['avg_lookup_ms'] = round(aggregated['cache']['avg_lookup_ms'] / aggregated['cache']['lookups'], 2)
            
            return aggregated
            
        except Exception as e:
            self.logger.error(f"Error getting metrics: {str(e)}")
            return {}
    
    def _cleanup_old_metrics(self) -> None:
        """Clean up metrics older than 1 hour."""
        try:
            current_time = int(time.time())
            cutoff_time = current_time - (60 * 60)  # 1 hour
            
            old_keys = []
            for minute_key in self._metrics.keys():
                minute_timestamp = int(minute_key) * 60
                if minute_timestamp < cutoff_time:
                    old_keys.append(minute_key)
            
            for old_key in old_keys:
                del self._metrics[old_key]
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old metrics: {str(e)}")

    def record_cache_lookup(self, user_hash: str, candidate_count: int, best_score: float,
                            lookup_ms: int, hit: bool) -> None:
        """Record per-look-up cache metrics, aggregated per minute and per user."""
        try:
            timestamp = int(time.time())
            minute_key = f"{timestamp // 60}"
            if minute_key not in self._metrics:
                self._metrics[minute_key] = {
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'total_processing_time': 0,
                    'endpoints': {},
                    'status_codes': {},
                    'client_ips': {},
                    'total_tokens': 0,
                    'total_cost': 0.0,
                    'total_cost_saved': 0.0,
                    'cache_hits': 0,
                    'llm_calls': 0,
                    'cache': {
                        'lookups': 0,
                        'hits': 0,
                        'total_lookup_ms': 0,
                        'best_score_max': 0.0,
                        'per_user': {}
                    }
                }
            m = self._metrics[minute_key]['cache']
            m['lookups'] += 1
            if hit:
                m['hits'] += 1
            m['total_lookup_ms'] += lookup_ms
            if best_score is not None:
                m['best_score_max'] = max(m['best_score_max'], float(best_score))
            # Per-user
            if user_hash not in m['per_user']:
                m['per_user'][user_hash] = {'lookups': 0, 'hits': 0}
            m['per_user'][user_hash]['lookups'] += 1
            if hit:
                m['per_user'][user_hash]['hits'] += 1
            # Periodic cleanup
            self._cleanup_old_metrics()
        except Exception as e:
            self.logger.error(f"Error recording cache lookup metric: {str(e)}")


# Global instances
proxy_logger = ProxyLogger()
metrics_collector = MetricsCollector()
