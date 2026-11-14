from dataclasses import dataclass, field

from core.settings import Settings


@dataclass
class GateTicket:
    ip: str
    pending: bool = True
    closed: bool = False


@dataclass
class ConnectionGate:
    max_total: int
    max_pending: int
    max_pending_per_ip: int
    _total: int = 0
    _pending: int = 0
    _pending_by_ip: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_settings(cls, config: Settings) -> "ConnectionGate":
        return cls(
            max_total=config.ws_max_connections,
            max_pending=config.ws_max_pending,
            max_pending_per_ip=config.ws_max_pending_per_ip,
        )

    def enter(self, ip: str) -> GateTicket | None:
        if self._total >= self.max_total or self._pending >= self.max_pending:
            return None
        if self._pending_by_ip.get(ip, 0) >= self.max_pending_per_ip:
            return None
        self._total += 1
        self._pending += 1
        self._pending_by_ip[ip] = self._pending_by_ip.get(ip, 0) + 1
        return GateTicket(ip)

    def authenticated(self, ticket: GateTicket) -> None:
        if ticket.pending and not ticket.closed:
            self._leave_pending(ticket)

    def leave(self, ticket: GateTicket) -> None:
        if ticket.closed:
            return
        if ticket.pending:
            self._leave_pending(ticket)
        ticket.closed = True
        self._total -= 1

    def _leave_pending(self, ticket: GateTicket) -> None:
        ticket.pending = False
        self._pending -= 1
        left = self._pending_by_ip[ticket.ip] - 1
        if left:
            self._pending_by_ip[ticket.ip] = left
        else:
            del self._pending_by_ip[ticket.ip]
