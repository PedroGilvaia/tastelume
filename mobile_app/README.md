# Tastelume — app Flutter

Flutter (Dart) com arquitetura **MVVM + Provider**. Fala com os 4 microserviços (portas 8001–8004).

## Primeira execução (Windows PowerShell)

Pré-requisitos: [Flutter SDK](https://docs.flutter.dev/get-started/install/windows), Android Studio (emulador) e o backend a correr (`docker compose up --build` na raiz do repositório).

```powershell
cd mobile_app
.\setup_platforms.ps1        # gera android/ e ios/ e aplica permissões (Internet, HTTP, câmara)
flutter analyze
flutter test
flutter run                  # com o emulador Android aberto
```

Se o PowerShell bloquear o script: `Set-ExecutionPolicy -Scope Process Bypass` e volta a executar.

### Configuração manual (alternativa ao script)

Depois de `flutter create --org pt.tastelume --project-name tastelume --platforms=android,ios .`:

- `android/app/src/main/AndroidManifest.xml` — antes de `<application`: `<uses-permission android:name="android.permission.INTERNET"/>` e no `<application` acrescenta `android:usesCleartextTraffic="true"`.
- `ios/Runner/Info.plist` — chaves `NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription` e `NSAppTransportSecurity` → `NSAllowsArbitraryLoads = true`.

## Endereço do servidor

| Onde corre a app | Anfitrião |
|---|---|
| Emulador Android | `10.0.2.2` (valor por omissão) |
| Simulador iOS | `localhost` (valor por omissão) |
| Telemóvel físico | IP do PC na rede local, p. ex. `192.168.1.20` (porta 8001–8004 abertas na firewall do Windows) |

Muda-se na app (ícone de servidor no ecrã de entrada; fica guardado) ou ao arrancar:
`flutter run --dart-define=API_HOST=192.168.1.20`.

## Dados de demonstração

Com o backend a correr: `python scripts/seed.py` (na raiz). Cria 5 utilizadores, 13 receitas com fotografia, gostos, avaliações, comentários, seguidores, uma lista de favoritos, uma partilha e mensagens. Todas as contas usam a password `Tastelume123` (ex.: `ana_cozinha`).

## Estrutura

```
lib/
├── main.dart, app.dart          # arranque, Providers, AuthGate
├── core/                        # ApiClient (JWT, timeouts, erros), configuração, formatação, token seguro
├── models/                      # classes de dados (JSON → objetos)
├── services/backend.dart        # UsersApi, RecipeApi, InteractionApi, ActivityApi
├── viewmodels/                  # estado e lógica de cada ecrã (ChangeNotifier)
└── views/                       # ecrãs e widgets
test/                            # testes unitários
```

## Funcionalidades

Registo/login (JWT em armazenamento seguro) · feed com categorias, ordenação, «Para ti» (personalizado) e paginação · pesquisa de receitas (texto/ingrediente) e utilizadores · detalhe com gostos, avaliação, comentários (editar/apagar), favoritos, partilha e receitas relacionadas · **criar/editar receita com fotografia da câmara** (ou galeria) · perfis, seguir/deixar de seguir · notificações com emblema · estatísticas (totais, gráfico diário, top de receitas) · mensagens (conversas e receitas partilhadas).

## Degradação graciosa

Cada ecrã separa os dados por serviço e falha só na parte afetada:

- Sem **Users Service**: o feed e as receitas continuam (autor aparece como «Autor #n»); login e perfis mostram erro com «Tentar novamente».
- Sem **Interaction Service**: a receita abre; a zona de gostos/comentários mostra um aviso e permite repetir.
- Sem **Activity Service**: tudo funciona; o emblema não atualiza e as estatísticas mostram erro nesse bloco.
- Sem **Recipe Service**: perfis, mensagens e notificações continuam.
- Sem rede ao arrancar com sessão guardada: ecrã «sem ligação» com opção de tentar de novo, alterar o servidor ou sair.
- Token expirado: a app volta ao login com uma mensagem, fechando os ecrãs abertos.
- Foto que falha ao enviar: a receita fica guardada e o utilizador é avisado.
