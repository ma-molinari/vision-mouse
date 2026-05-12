# Validacao do MVP VisionMouse Pro

## Stack implementada

- `MediaPipe` para inferencia de landmarks da mao em `src/vision_mouse/vision/mediapipe_provider.py`
- `OpenCV` para captura e normalizacao da webcam em `src/vision_mouse/capture/session.py`
- `pynput` para movimento/clique/drag do ponteiro em `src/vision_mouse/platform/macos/input.py`
- `osascript` para navegacao de workspace no macOS em `src/vision_mouse/platform/macos/workspace.py`

## Thresholds iniciais

- `min_detection_confidence`: `0.65`
- `min_tracking_confidence`: `0.55`
- `operational_window`: `x=0.15..0.85`, `y=0.12..0.88`
- `smoothing.alpha`: `0.32`
- `smoothing.min_confidence`: `0.65`
- `smoothing.reacquire_frames`: `3`
- `left_pinch_threshold`: `0.055`
- `right_pinch_threshold`: `0.060`
- `pinch_release_threshold`: `0.085`
- `drag_hold_ms`: `320`
- `workspace_swipe_delta`: `0.18`
- `workspace_history_ms`: `350`

## Evidencia automatizada

Comando executado:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Cobertura validada pelos testes:

- contratos de dominio independentes de framework
- bootstrap seguro e gating por permissao
- mapeamento camera-tela com janela operacional
- gate de confianca e suavizacao temporal
- clique principal, arraste sustentado e workspace swipe
- bloqueio do roteador quando o estado operacional nao e seguro

## Checklist manual pendente no macOS

1. Instalar dependencias do projeto.
2. Executar `PYTHONPATH=src python3 -m vision_mouse.main`.
3. Confirmar que sem camera/acessibilidade o estado permanece bloqueado.
4. Confirmar que com permissoes liberadas o pipeline entra em `ready`.
5. Validar movimento de cursor, clique esquerdo, clique direito e arraste.
6. Validar gesto de workspace sem conflito com arraste.
7. Desconectar ou bloquear a camera e confirmar transicao segura para degradado.

## Limitacoes atuais

- A verificacao ponta a ponta com webcam e permissoes reais nao foi executada neste ambiente.
- A deteccao de permissao de camera usa sonda com `OpenCV`, suficiente para gating tecnico do MVP, mas ainda depende de validacao em hardware real.
