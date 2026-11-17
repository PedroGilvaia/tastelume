import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/config.dart';

void showSnack(BuildContext context, String message) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(message)));
}

/// Ecrã/bloco de erro com botão para tentar novamente.
class ErrorState extends StatelessWidget {
  const ErrorState({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off, size: 48, color: Colors.grey),
              const SizedBox(height: 12),
              Text(message, textAlign: TextAlign.center),
              if (onRetry != null) ...[
                const SizedBox(height: 16),
                FilledButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Tentar novamente')),
              ],
            ],
          ),
        ),
      );
}

class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 48, color: Colors.grey),
              const SizedBox(height: 12),
              Text(message,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.grey)),
            ],
          ),
        ),
      );
}

/// Faixa discreta para quando só uma parte do ecrã está indisponível.
class InlineNotice extends StatelessWidget {
  const InlineNotice({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.amber.shade50,
          border: Border.all(color: Colors.amber.shade300),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline, color: Colors.amber.shade800, size: 20),
            const SizedBox(width: 8),
            Expanded(
                child: Text(message, style: const TextStyle(fontSize: 13))),
            if (onRetry != null)
              TextButton(onPressed: onRetry, child: const Text('Tentar')),
          ],
        ),
      );
}

/// Imagem da receita (ou um marcador se não houver foto ou se o servidor de imagens falhar).
class RecipeImage extends StatelessWidget {
  const RecipeImage(
      {super.key, required this.imageUrl, this.height = 160, this.width});

  final String? imageUrl;
  final double height;
  final double? width;

  @override
  Widget build(BuildContext context) {
    final url = context.read<ApiConfig>().imageUrl(imageUrl);
    final placeholder = Container(
      height: height,
      width: width ?? double.infinity,
      color: Colors.orange.shade50,
      child: Icon(Icons.restaurant,
          size: height / 3, color: Colors.orange.shade200),
    );
    if (url == null) return placeholder;
    return Image.network(
      url,
      height: height,
      width: width ?? double.infinity,
      fit: BoxFit.cover,
      errorBuilder: (_, __, ___) => placeholder,
      loadingBuilder: (context, child, progress) =>
          progress == null ? child : placeholder,
    );
  }
}

class StarRating extends StatelessWidget {
  const StarRating(
      {super.key, required this.value, this.size = 20, this.onChanged});

  /// Valor (pode ter decimais) a mostrar; `null` = sem avaliação.
  final double? value;
  final double size;

  /// Se definido, as estrelas são tocáveis.
  final ValueChanged<int>? onChanged;

  @override
  Widget build(BuildContext context) {
    final v = value ?? 0;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 1; i <= 5; i++)
          GestureDetector(
            onTap: onChanged == null ? null : () => onChanged!(i),
            child: Icon(
              v >= i - 0.25
                  ? Icons.star
                  : (v >= i - 0.75 ? Icons.star_half : Icons.star_border),
              size: size,
              color: Colors.amber.shade700,
            ),
          ),
      ],
    );
  }
}

class Avatar extends StatelessWidget {
  const Avatar({super.key, required this.name, this.radius = 20});

  final String name;
  final double radius;

  @override
  Widget build(BuildContext context) => CircleAvatar(
        radius: radius,
        backgroundColor: Colors.orange.shade100,
        child: Text(
          name.isEmpty ? '?' : name.characters.first.toUpperCase(),
          style: TextStyle(
              color: Colors.orange.shade900,
              fontWeight: FontWeight.bold,
              fontSize: radius * 0.9),
        ),
      );
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 8),
        child: Text(text,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(fontWeight: FontWeight.bold)),
      );
}

Future<bool> confirm(BuildContext context, String title, String message,
    {String action = 'Confirmar'}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancelar')),
        FilledButton(
            onPressed: () => Navigator.pop(ctx, true), child: Text(action)),
      ],
    ),
  );
  return result ?? false;
}

/// Pede uma linha de texto. Devolve `null` se o utilizador cancelar.
Future<String?> promptText(
  BuildContext context, {
  required String title,
  String label = '',
  String initial = '',
  int maxLength = 1000,
  String action = 'Guardar',
  int maxLines = 1,
}) {
  final controller = TextEditingController(text: initial);
  return showDialog<String>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: controller,
        autofocus: true,
        maxLength: maxLength,
        maxLines: maxLines,
        decoration: InputDecoration(labelText: label),
      ),
      actions: [
        TextButton(
            onPressed: () => Navigator.pop(ctx), child: const Text('Cancelar')),
        FilledButton(
          onPressed: () {
            final text = controller.text.trim();
            Navigator.pop(ctx, text.isEmpty ? null : text);
          },
          child: Text(action),
        ),
      ],
    ),
  );
}

/// Dispara [onEnd] quando a lista está perto do fim (paginação infinita).
class EndlessScroll extends StatelessWidget {
  const EndlessScroll({super.key, required this.onEnd, required this.child});

  final VoidCallback onEnd;
  final Widget child;

  @override
  Widget build(BuildContext context) =>
      NotificationListener<ScrollNotification>(
        onNotification: (n) {
          if (n.metrics.pixels >= n.metrics.maxScrollExtent - 300) onEnd();
          return false;
        },
        child: child,
      );
}
