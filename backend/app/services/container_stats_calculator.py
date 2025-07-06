"""
Container Statistics Calculator

This service extracts and calculates container resource usage statistics
from raw Docker stats data, reducing complexity in API endpoints.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from app.schemas.container import ContainerStats
from app.core.logging import logger


@dataclass
class CpuStats:
    """CPU statistics data"""
    cpu_percent: float
    cpu_count: int
    throttled_time: Optional[float] = None
    throttled_periods: Optional[int] = None


@dataclass
class MemoryStats:
    """Memory statistics data"""
    usage: int
    limit: int
    percent: float
    cache: Optional[int] = None
    rss: Optional[int] = None


@dataclass
class NetworkStats:
    """Network I/O statistics"""
    rx_bytes: int
    tx_bytes: int
    rx_packets: Optional[int] = None
    tx_packets: Optional[int] = None
    rx_errors: Optional[int] = None
    tx_errors: Optional[int] = None


@dataclass
class BlockIoStats:
    """Block I/O statistics"""
    read_bytes: int
    write_bytes: int
    read_ops: Optional[int] = None
    write_ops: Optional[int] = None


class ContainerStatsCalculator:
    """Service for calculating container statistics from raw Docker data"""
    
    def calculate_stats(self, raw_stats: Dict[str, Any]) -> ContainerStats:
        """
        Calculate container statistics from raw Docker stats
        
        Args:
            raw_stats: Raw statistics from Docker API
            
        Returns:
            Calculated ContainerStats object
        """
        try:
            cpu = self._calculate_cpu_stats(raw_stats)
            memory = self._calculate_memory_stats(raw_stats)
            network = self._calculate_network_stats(raw_stats)
            block_io = self._calculate_block_io_stats(raw_stats)
            pids = self._get_pid_count(raw_stats)
            
            return ContainerStats(
                cpu_percent=cpu.cpu_percent,
                memory_usage=memory.usage,
                memory_limit=memory.limit,
                memory_percent=memory.percent,
                network_rx=network.rx_bytes,
                network_tx=network.tx_bytes,
                block_read=block_io.read_bytes,
                block_write=block_io.write_bytes,
                pids=pids
            )
            
        except Exception as e:
            logger.error(f"Error calculating container stats: {e}")
            # Return zero stats on error
            return ContainerStats(
                cpu_percent=0.0,
                memory_usage=0,
                memory_limit=0,
                memory_percent=0.0,
                network_rx=0,
                network_tx=0,
                block_read=0,
                block_write=0,
                pids=0
            )
    
    def _calculate_cpu_stats(self, stats: Dict[str, Any]) -> CpuStats:
        """Calculate CPU usage percentage"""
        try:
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})
            
            # Get CPU usage values
            cpu_usage = cpu_stats.get("cpu_usage", {})
            precpu_usage = precpu_stats.get("cpu_usage", {})
            
            cpu_total = cpu_usage.get("total_usage", 0)
            precpu_total = precpu_usage.get("total_usage", 0)
            
            # Calculate deltas
            cpu_delta = cpu_total - precpu_total
            
            # System CPU usage
            system_cpu = cpu_stats.get("system_cpu_usage", 0)
            pre_system_cpu = precpu_stats.get("system_cpu_usage", 0)
            system_delta = system_cpu - pre_system_cpu
            
            # Number of CPU cores
            online_cpus = cpu_stats.get("online_cpus", 1)
            if online_cpus == 0:
                online_cpus = len(cpu_usage.get("percpu_usage", [1]))
            
            # Calculate percentage
            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0
            
            # Get throttling info if available
            throttling_data = cpu_stats.get("throttling_data", {})
            
            return CpuStats(
                cpu_percent=round(cpu_percent, 2),
                cpu_count=online_cpus,
                throttled_time=throttling_data.get("throttled_time"),
                throttled_periods=throttling_data.get("throttled_periods")
            )
            
        except Exception as e:
            logger.warning(f"Error calculating CPU stats: {e}")
            return CpuStats(cpu_percent=0.0, cpu_count=1)
    
    def _calculate_memory_stats(self, stats: Dict[str, Any]) -> MemoryStats:
        """Calculate memory usage statistics"""
        try:
            memory_stats = stats.get("memory_stats", {})
            
            # Get memory values
            usage = memory_stats.get("usage", 0)
            limit = memory_stats.get("limit", 0)
            
            # Some systems report very high limit values
            if limit > 9223372036854775807:  # Max int64 / 2
                limit = 0
            
            # Calculate percentage
            memory_percent = 0.0
            if limit > 0:
                memory_percent = (usage / limit) * 100.0
            
            # Get cache and RSS if available
            stats_detail = memory_stats.get("stats", {})
            cache = stats_detail.get("cache", 0)
            rss = stats_detail.get("rss", usage - cache if cache else None)
            
            return MemoryStats(
                usage=usage,
                limit=limit,
                percent=round(memory_percent, 2),
                cache=cache,
                rss=rss
            )
            
        except Exception as e:
            logger.warning(f"Error calculating memory stats: {e}")
            return MemoryStats(usage=0, limit=0, percent=0.0)
    
    def _calculate_network_stats(self, stats: Dict[str, Any]) -> NetworkStats:
        """Calculate network I/O statistics"""
        try:
            networks = stats.get("networks", {})
            
            # Aggregate stats from all network interfaces
            total_rx_bytes = 0
            total_tx_bytes = 0
            total_rx_packets = 0
            total_tx_packets = 0
            total_rx_errors = 0
            total_tx_errors = 0
            
            for interface, net_stats in networks.items():
                total_rx_bytes += net_stats.get("rx_bytes", 0)
                total_tx_bytes += net_stats.get("tx_bytes", 0)
                total_rx_packets += net_stats.get("rx_packets", 0)
                total_tx_packets += net_stats.get("tx_packets", 0)
                total_rx_errors += net_stats.get("rx_errors", 0)
                total_tx_errors += net_stats.get("tx_errors", 0)
            
            return NetworkStats(
                rx_bytes=total_rx_bytes,
                tx_bytes=total_tx_bytes,
                rx_packets=total_rx_packets if total_rx_packets > 0 else None,
                tx_packets=total_tx_packets if total_tx_packets > 0 else None,
                rx_errors=total_rx_errors if total_rx_errors > 0 else None,
                tx_errors=total_tx_errors if total_tx_errors > 0 else None
            )
            
        except Exception as e:
            logger.warning(f"Error calculating network stats: {e}")
            return NetworkStats(rx_bytes=0, tx_bytes=0)
    
    def _calculate_block_io_stats(self, stats: Dict[str, Any]) -> BlockIoStats:
        """Calculate block I/O statistics"""
        try:
            blkio_stats = stats.get("blkio_stats", {})
            
            # Sum up read and write bytes
            read_bytes = 0
            write_bytes = 0
            read_ops = 0
            write_ops = 0
            
            # Process io_service_bytes_recursive
            io_service_bytes = blkio_stats.get("io_service_bytes_recursive", [])
            for entry in io_service_bytes:
                op = entry.get("op", "").lower()
                value = entry.get("value", 0)
                
                if op == "read":
                    read_bytes += value
                elif op == "write":
                    write_bytes += value
            
            # Process io_serviced_recursive for operation counts
            io_serviced = blkio_stats.get("io_serviced_recursive", [])
            for entry in io_serviced:
                op = entry.get("op", "").lower()
                value = entry.get("value", 0)
                
                if op == "read":
                    read_ops += value
                elif op == "write":
                    write_ops += value
            
            return BlockIoStats(
                read_bytes=read_bytes,
                write_bytes=write_bytes,
                read_ops=read_ops if read_ops > 0 else None,
                write_ops=write_ops if write_ops > 0 else None
            )
            
        except Exception as e:
            logger.warning(f"Error calculating block I/O stats: {e}")
            return BlockIoStats(read_bytes=0, write_bytes=0)
    
    def _get_pid_count(self, stats: Dict[str, Any]) -> int:
        """Get current PID count"""
        try:
            pids_stats = stats.get("pids_stats", {})
            return pids_stats.get("current", 0)
        except Exception:
            return 0
    
    def get_extended_stats(self, raw_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get extended statistics including additional metrics
        
        Returns a dictionary with all calculated stats plus extended info
        """
        basic_stats = self.calculate_stats(raw_stats)
        
        # Calculate extended metrics
        cpu = self._calculate_cpu_stats(raw_stats)
        memory = self._calculate_memory_stats(raw_stats)
        network = self._calculate_network_stats(raw_stats)
        block_io = self._calculate_block_io_stats(raw_stats)
        
        return {
            "basic": basic_stats.dict(),
            "extended": {
                "cpu": {
                    "percent": cpu.cpu_percent,
                    "count": cpu.cpu_count,
                    "throttled_time": cpu.throttled_time,
                    "throttled_periods": cpu.throttled_periods
                },
                "memory": {
                    "usage": memory.usage,
                    "limit": memory.limit,
                    "percent": memory.percent,
                    "cache": memory.cache,
                    "rss": memory.rss,
                    "usage_human": self._humanize_bytes(memory.usage),
                    "limit_human": self._humanize_bytes(memory.limit)
                },
                "network": {
                    "rx_bytes": network.rx_bytes,
                    "tx_bytes": network.tx_bytes,
                    "rx_packets": network.rx_packets,
                    "tx_packets": network.tx_packets,
                    "rx_errors": network.rx_errors,
                    "tx_errors": network.tx_errors,
                    "rx_human": self._humanize_bytes(network.rx_bytes),
                    "tx_human": self._humanize_bytes(network.tx_bytes)
                },
                "block_io": {
                    "read_bytes": block_io.read_bytes,
                    "write_bytes": block_io.write_bytes,
                    "read_ops": block_io.read_ops,
                    "write_ops": block_io.write_ops,
                    "read_human": self._humanize_bytes(block_io.read_bytes),
                    "write_human": self._humanize_bytes(block_io.write_bytes)
                }
            }
        }
    
    def _humanize_bytes(self, bytes_value: int) -> str:
        """Convert bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"


# Global instance
_calculator = ContainerStatsCalculator()


def calculate_container_stats(raw_stats: Dict[str, Any]) -> ContainerStats:
    """Calculate container statistics (convenience function)"""
    return _calculator.calculate_stats(raw_stats)