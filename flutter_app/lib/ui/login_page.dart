import "package:flutter/material.dart";

import "../app_state.dart";

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.state});
  final AppState state;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _baseUrl = TextEditingController();
  final _email = TextEditingController();
  final _pw = TextEditingController();
  String? _msg;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _baseUrl.text = widget.state.baseUrl;
  }

  @override
  void dispose() {
    _baseUrl.dispose();
    _email.dispose();
    _pw.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("登录")),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            TextField(
              controller: _baseUrl,
              decoration: const InputDecoration(
                labelText: "服务器地址",
                hintText: "https://todo.example.com",
              ),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 10),
            TextField(controller: _email, decoration: const InputDecoration(labelText: "邮箱"), keyboardType: TextInputType.emailAddress),
            const SizedBox(height: 10),
            TextField(controller: _pw, decoration: const InputDecoration(labelText: "密码"), obscureText: true),
            const SizedBox(height: 14),
            if (_msg != null) Text(_msg!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            const Spacer(),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _busy ? null : () => _do(register: true),
                    child: const Text("注册"),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton(
                    onPressed: _busy ? null : () => _do(register: false),
                    child: _busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Text("登录"),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _do({required bool register}) async {
    setState(() {
      _msg = null;
      _busy = true;
    });
    try {
      final baseUrl = _baseUrl.text.trim();
      if (!baseUrl.startsWith("http")) throw Exception("服务器地址必须以 http/https 开头");
      await widget.state.setBaseUrl(baseUrl);
      final email = _email.text.trim();
      final pw = _pw.text;
      if (register) {
        await widget.state.register(email, pw);
      } else {
        await widget.state.login(email, pw);
      }
    } catch (e) {
      setState(() => _msg = "$e");
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

