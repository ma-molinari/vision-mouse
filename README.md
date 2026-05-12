# Vision Mouse

Controle de cursor por gestos de mao usando webcam, com processamento local em Python e integracao com o macOS.

O projeto implementa um MVP de interacao hands-free: captura frames da webcam, detecta landmarks da mao com MediaPipe, traduz movimentos e posturas em intencoes e emite eventos nativos de cursor no macOS.

## O que o projeto faz

- move o cursor a partir da posicao da mao
- reconhece clique esquerdo e clique direito por pinca
- sustenta arraste com pinca prolongada
- faz scroll com gesto de dois dedos
- troca de workspace no macOS com gesto horizontal de mao aberta
- aplica suavizacao temporal e assistencias de ponteiro para reduzir jitter
- oferece calibracao guiada e perfil persistido em disco

## Stack

- Python 3.9+
- MediaPipe Tasks para hand tracking
- OpenCV para captura e normalizacao da webcam
- `pynput` para input do mouse
- AppleScript / `osascript` para integracoes nativas do macOS

## Requisitos

- macOS
- webcam funcional
- Python instalado fora do runtime embutido do Xcode
- permissao de Camera
- permissao de Accessibility

O `Makefile` ja protege contra o uso de um interpretador Python do Xcode, porque esse runtime pode instalar uma variante de `mediapipe` incompativel com este MVP.

## Instalacao

Crie um ambiente virtual e instale as dependencias:

```bash
make venv
make install
```

Para desenvolvimento em modo editavel:

```bash
make dev-install
```

## Como executar

Execucao principal:

```bash
make run
```

Ou diretamente pelo modulo:

```bash
PYTHONPATH=src python3 -m vision_mouse.main
```

Calibracao guiada:

```bash
PYTHONPATH=src python3 -m vision_mouse.main calibrate
```

## Permissoes no macOS

Na inicializacao, o app consulta o estado nativo da permissao de Camera no macOS e, na primeira execucao, dispara o prompt de autorizacao automaticamente antes de subir o pipeline.

Se a permissao de acessibilidade nao estiver liberada, o bootstrap tenta abrir o painel correto do sistema:

- `System Settings > Privacy & Security > Accessibility`

Sem camera ou acessibilidade, o pipeline permanece bloqueado e nao emite eventos de input.

## Gestos suportados no MVP

| Gesto | Acao |
| --- | --- |
| Movimento da mao com ponto de referencia do indicador | Mover cursor |
| Pinca entre polegar e indicador | Clique esquerdo |
| Pinca sustentada entre polegar e indicador | Inicio/manutencao/fim de arraste |
| Pinca entre polegar e dedo medio | Clique direito |
| Movimento vertical com dois dedos | Scroll |
| Movimento horizontal rapido com mao aberta | Troca de workspace no macOS |

## Calibracao e perfil

A calibracao guiada mede alcance, estabilidade e distancia natural de pinca para ajustar partes do pipeline:

- janela operacional do cursor
- parametros de suavizacao
- deadzone e resistencias do pointer assist
- thresholds principais de gesto

Por padrao, o perfil eh salvo em:

```text
~/.vision_mouse/profile.json
```

Voce pode sobrescrever esse caminho com:

```bash
VISION_MOUSE_PROFILE_PATH=/caminho/para/profile.json
```

## Comandos uteis

```bash
make help
make test
make build
make package
make clean
```

## Estrutura do projeto

```text
src/vision_mouse/
  app/             bootstrap e coordenacao do estado operacional
  calibration/     calibracao guiada e persistencia de perfil
  capture/         sessao de webcam
  domain/          contratos e tipos centrais
  filters/         gate de confianca e suavizacao temporal
  gestures/        reconhecimento de cliques, drag, scroll e navegacao
  mapping/         mapeamento camera -> tela e pointer assist
  observability/   telemetria do pipeline
  pipeline/        runtime e roteamento de intencoes
  platform/macos/  input nativo, permissoes e automacoes do sistema
  vision/          provider de landmarks com MediaPipe
```

## Fluxo de alto nivel

1. A webcam captura um frame.
2. O frame eh normalizado e enviado ao MediaPipe.
3. O detector retorna landmarks da mao.
4. O pipeline filtra confianca e suaviza a movimentacao.
5. O motor de gestos produz intencoes semanticas.
6. O roteador converte essas intencoes em eventos nativos do macOS.

## Documentacao adicional

- [docs/TDD.md](/Users/ma-molinari/Documents/projects/m-tech/vision-mouse/docs/TDD.md)
- [docs/MVP_VALIDATION.md](/Users/ma-molinari/Documents/projects/m-tech/vision-mouse/docs/MVP_VALIDATION.md)

## Limitacoes atuais

- o foco atual eh exclusivamente macOS
- o processamento assume uma unica mao por vez
- a experiencia depende bastante de iluminacao, enquadramento e ergonomia
- o projeto ja possui gancho para macros, mas essa parte ainda esta em preparacao

## Proximos passos naturais

- validar ergonomia em hardware real por sessoes mais longas
- expandir calibracao para multiplos monitores
- adicionar configuracao de gestos por perfil
- evoluir overlay e feedback visual de onboarding
