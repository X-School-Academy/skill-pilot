from __future__ import annotations

import json
import os
import select
import shlex
import socket
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_ENGINE_ROOT = str(Path(__file__).resolve().parents[2])
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

import json5_io as json5

import paramiko
from sshtunnel import SSHTunnelForwarder


@dataclass
class SSHProfile:
    name: str
    host: str
    user: str
    port: int = 22
    password: str | None = None
    key: str | None = None
    known_hosts: str | None = None
    timeout_ms: int = 60000
    max_chars: int | None = 1000
    sudo_password: str | None = None


class _RemoteForwarder:
    """Accept channels from a remote port-forward and relay to a local address."""

    def __init__(
        self,
        transport: paramiko.Transport,
        local_host: str,
        local_port: int,
        remote_bind_host: str,
        remote_bind_port: int,
    ) -> None:
        self.transport = transport
        self.local_host = local_host
        self.local_port = local_port
        self.remote_bind_host = remote_bind_host
        self.remote_bind_port = remote_bind_port
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        try:
            self.transport.cancel_port_forward(self.remote_bind_host, self.remote_bind_port)
        except Exception:
            pass
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _accept_loop(self) -> None:
        while self._running:
            chan = self.transport.accept(timeout=1.0)
            if chan is None:
                continue
            t = threading.Thread(target=self._relay, args=(chan,), daemon=True)
            t.start()

    @property
    def is_active(self) -> bool:
        if not self._running:
            return False
        try:
            return self.transport.is_active()
        except Exception:
            return False

    def _relay(self, remote_chan: paramiko.Channel) -> None:
        local_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            local_sock.connect((self.local_host, self.local_port))
        except Exception:
            remote_chan.close()
            local_sock.close()
            return

        try:
            while True:
                r, _, _ = select.select([local_sock, remote_chan], [], [], 1.0)
                if local_sock in r:
                    data = local_sock.recv(16384)
                    if not data:
                        break
                    remote_chan.sendall(data)
                if remote_chan in r:
                    data = remote_chan.recv(16384)
                    if not data:
                        break
                    local_sock.sendall(data)
        except Exception:
            pass
        finally:
            local_sock.close()
            remote_chan.close()


class SSHClientPool:
    def __init__(self) -> None:
        self._profiles: dict[str, SSHProfile] = {}
        self._clients: dict[str, paramiko.SSHClient] = {}
        self._locks: dict[str, threading.RLock] = {}
        self._tunnels: dict[str, SSHTunnelForwarder | _RemoteForwarder] = {}
        self._tunnel_meta: dict[str, dict[str, str | int]] = {}
        self._tunnel_counter = 0
        self._tunnel_lock = threading.RLock()

    def load_profiles(self, path: str | None) -> None:
        if not path:
            return
        if not os.path.isfile(path):
            raise ValueError(f"ssh config not found: {path}")
        with open(path) as f:
            raw = json5.load(f)
        profiles = raw.get("profiles", {})
        for name, item in profiles.items():
            self._profiles[name] = SSHProfile(
                name=name,
                host=item["host"],
                user=item["user"],
                port=int(item.get("port", 22)),
                password=item.get("password"),
                key=item.get("key"),
                known_hosts=item.get("knownHosts"),
                timeout_ms=int(item.get("timeoutMs", 60000)),
                max_chars=(
                    None
                    if str(item.get("maxChars", "1000")).lower() in {"none", "0", "-1"}
                    else int(item.get("maxChars", 1000))
                ),
                sudo_password=item.get("sudoPassword"),
            )
            self._locks[name] = threading.RLock()

    def get_profile(self, name: str) -> SSHProfile:
        profile = self._profiles.get(name)
        if profile is None:
            raise ValueError(f"unknown ssh profile: {name}")
        return profile

    def get_client(self, name: str) -> paramiko.SSHClient:
        profile = self.get_profile(name)
        lock = self._locks[name]
        with lock:
            client = self._clients.get(name)
            if client is not None:
                t = client.get_transport()
                if t is not None and t.is_active():
                    return client
                try:
                    client.close()
                except Exception:
                    pass

            client = paramiko.SSHClient()
            if profile.known_hosts:
                client.load_host_keys(profile.known_hosts)
                client.set_missing_host_key_policy(paramiko.RejectPolicy())
            else:
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            params = {
                "hostname": profile.host,
                "port": profile.port,
                "username": profile.user,
                "timeout": 20,
            }
            if profile.password:
                params["password"] = profile.password
            if profile.key:
                params["key_filename"] = profile.key
            client.connect(**params)
            self._clients[name] = client
            return client

    def exec_command(self, profile: str, command: str, timeout_ms: int | None = None) -> tuple[str, str, int]:
        p = self.get_profile(profile)
        client = self.get_client(profile)
        timeout_sec = (timeout_ms or p.timeout_ms) / 1000
        _, stdout_f, stderr_f = client.exec_command(command, timeout=timeout_sec)
        stdout = stdout_f.read().decode("utf-8", errors="replace")
        stderr = stderr_f.read().decode("utf-8", errors="replace")
        exit_code = stdout_f.channel.recv_exit_status()
        return stdout, stderr, exit_code

    def sudo_exec_command(self, profile: str, command: str, timeout_ms: int | None = None) -> tuple[str, str, int]:
        p = self.get_profile(profile)
        client = self.get_client(profile)
        timeout_sec = (timeout_ms or p.timeout_ms) / 1000
        sudo_pwd = p.sudo_password
        if sudo_pwd:
            wrapped = f"sudo -p '' -S sh -c {shlex.quote(command)}"
            stdin_f, stdout_f, stderr_f = client.exec_command(wrapped, timeout=timeout_sec)
            stdin_f.write(sudo_pwd + "\n")
            stdin_f.flush()
            try:
                stdin_f.channel.shutdown_write()
            except Exception:
                pass
        else:
            wrapped = f"sudo -n sh -c {shlex.quote(command)}"
            _, stdout_f, stderr_f = client.exec_command(wrapped, timeout=timeout_sec)
        stdout = stdout_f.read().decode("utf-8", errors="replace")
        stderr = stderr_f.read().decode("utf-8", errors="replace")
        exit_code = stdout_f.channel.recv_exit_status()
        return stdout, stderr, exit_code

    def scp_upload(
        self,
        profile: str,
        local_path: str,
        remote_path: str,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> str:
        client = self.get_client(profile)
        sftp = client.open_sftp()
        try:
            sftp.put(local_path, remote_path, callback=progress_cb)
            stat = sftp.stat(remote_path)
            return f"Uploaded {local_path} -> {profile}:{remote_path} ({stat.st_size} bytes)"
        finally:
            sftp.close()

    def scp_download(
        self,
        profile: str,
        remote_path: str,
        local_path: str,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> str:
        client = self.get_client(profile)
        sftp = client.open_sftp()
        try:
            sftp.get(remote_path, local_path, callback=progress_cb)
            size = os.path.getsize(local_path)
            return f"Downloaded {profile}:{remote_path} -> {local_path} ({size} bytes)"
        finally:
            sftp.close()

    def _next_tunnel_id(self) -> str:
        with self._tunnel_lock:
            self._tunnel_counter += 1
            return f"tunnel-{self._tunnel_counter}"

    def start_forward_remote_to_local(
        self,
        profile: str,
        remote_host: str,
        remote_port: int,
        local_port: int = 0,
    ) -> tuple[str, int]:
        p = self.get_profile(profile)
        kw: dict = {
            "ssh_username": p.user,
            "remote_bind_address": (remote_host, remote_port),
        }
        if local_port:
            kw["local_bind_address"] = ("127.0.0.1", local_port)
        else:
            kw["local_bind_address"] = ("127.0.0.1",)
        if p.password:
            kw["ssh_password"] = p.password
        if p.key:
            kw["ssh_pkey"] = p.key

        tun = SSHTunnelForwarder((p.host, p.port), **kw)
        tun.start()
        tid = self._next_tunnel_id()
        with self._tunnel_lock:
            self._tunnels[tid] = tun
            self._tunnel_meta[tid] = {
                "profile": profile,
                "direction": "L",
                "localPort": tun.local_bind_port,
                "remoteHost": remote_host,
                "remotePort": remote_port,
            }
        return tid, tun.local_bind_port

    def start_forward_local_to_remote(
        self,
        profile: str,
        local_host: str,
        local_port: int,
        remote_port: int,
        remote_host: str = "127.0.0.1",
    ) -> tuple[str, int]:
        client = self.get_client(profile)
        transport = client.get_transport()
        if transport is None:
            raise RuntimeError(f"SSH transport unavailable for profile {profile}")
        actual_port = transport.request_port_forward(remote_host, remote_port)
        fwd = _RemoteForwarder(transport, local_host, local_port, remote_host, actual_port)
        fwd.start()

        tid = self._next_tunnel_id()
        with self._tunnel_lock:
            self._tunnels[tid] = fwd
            self._tunnel_meta[tid] = {
                "profile": profile,
                "direction": "R",
                "localHost": local_host,
                "localPort": local_port,
                "remoteHost": remote_host,
                "remotePort": actual_port,
            }
        return tid, actual_port

    def stop_tunnel(self, tunnel_id: str) -> str:
        with self._tunnel_lock:
            entry = self._tunnels.pop(tunnel_id, None)
            self._tunnel_meta.pop(tunnel_id, None)
        if entry is None:
            raise ValueError(f"Unknown tunnel: {tunnel_id}")
        if isinstance(entry, SSHTunnelForwarder):
            entry.stop()
        else:
            entry.stop()
        return f"Tunnel {tunnel_id} stopped"

    def list_tunnels(self) -> list[dict]:
        with self._tunnel_lock:
            out = []
            for tid, meta in self._tunnel_meta.items():
                item = dict(meta)
                item["tunnelId"] = tid
                item["active"] = self._is_tunnel_active(tid)
                out.append(item)
            return out

    def get_tunnel(self, tunnel_id: str) -> dict:
        with self._tunnel_lock:
            if tunnel_id not in self._tunnel_meta:
                raise ValueError(f"Unknown tunnel: {tunnel_id}")
            item = dict(self._tunnel_meta[tunnel_id])
            item["tunnelId"] = tunnel_id
            item["active"] = self._is_tunnel_active(tunnel_id)
            return item

    def _is_tunnel_active(self, tunnel_id: str) -> bool:
        entry = self._tunnels.get(tunnel_id)
        if entry is None:
            return False
        if isinstance(entry, SSHTunnelForwarder):
            try:
                return bool(entry.is_active)
            except Exception:
                return False
        return entry.is_active

    def close_all(self) -> None:
        with self._tunnel_lock:
            for tid, tun in list(self._tunnels.items()):
                try:
                    if isinstance(tun, SSHTunnelForwarder):
                        tun.stop()
                    else:
                        tun.stop()
                except Exception:
                    pass
                self._tunnels.pop(tid, None)
                self._tunnel_meta.pop(tid, None)
        for name, client in list(self._clients.items()):
            try:
                client.close()
            except Exception:
                pass
            self._clients.pop(name, None)
