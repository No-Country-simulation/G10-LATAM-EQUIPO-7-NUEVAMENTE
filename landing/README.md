# NuevaMente — Deck web para el Demo Day

Presentación interactiva de seis momentos, pensada para acompañar un pitch de cinco minutos. HTML5, CSS, SVG y JavaScript vanilla; sin npm, build ni frameworks. Independiente del frontend principal.

## Recorrido

1. **Del documento al conocimiento:** un documento conectado con cuatro perfiles.
2. **Qué transforma NuevaMente:** documento → contexto → adaptación → cuatro formatos.
3. **Verlo en acción:** transición al producto real, abierto en otra pestaña.
4. **Lo que ocurre detrás:** arquitectura interactiva, generación inicial y corrección.
5. **El equipo:** ocho contribuciones destacadas y colaboradores, accesibles directamente en el recorrido.
6. **Por qué importa:** aprendizaje adaptado, calidad con evidencia y producto integrado; recursos para el jurado.

## Controles

Cada vista tiene una entrada breve y escalonada: conexiones del documento, transformación por etapas, recorrido de demo, aparición de arquitectura, integrantes y tarjetas de valor. Las animaciones se cancelan al navegar o salir de la pestaña y se omiten con movimiento reducido. No se reproducen en bucle ni cambian las dimensiones del contenido; la secuencia de arquitectura sigue bajo control del presentador.

En escritorio, la presentación ocupa la altura disponible de la ventana: cabecera y navegación permanecen visibles. Las composiciones se compactan según la altura y se ajustan automáticamente si el contenido supera el espacio disponible. El ajuste se recalcula al navegar, cambiar pasos, redimensionar o entrar en pantalla completa. En móvil se conserva el desplazamiento para mantener la legibilidad.

- Navegación inferior, botones anterior/siguiente y teclas izquierda/derecha o PageUp/PageDown. Home/End llevan al inicio/cierre. Los atajos no interceptan controles interactivos ni el diálogo.
- Enlaces directos: `#documento`, `#transformacion`, `#demo`, `#arquitectura`, `#equipo`, `#impacto`. El historial del navegador permite regresar entre vistas.
- Arquitectura: el panel inferior tiene dos columnas, explicación del paso y controles compactos (Reiniciar, Reproducir, Pausa y nueva evidencia). Reproducir recorre generación, evaluación y un caso que necesita corrección; termina con la respuesta de BackendAPI al Frontend, iluminando su flecha de retorno. Pausa conserva el paso; Reproducir continúa desde allí. Reiniciar restaura el diagrama general. Al terminar, cambiar de vista o salir de la pestaña, la reproducción se detiene. En móvil las columnas se apilan.
- Activar o desactivar “Requiere nueva evidencia” selecciona el camino del Revisor y reinicia la secuencia para mantenerla coherente.
- Seleccionar un nodo muestra su responsabilidad. Data/IA siempre permanece como evaluador independiente; BackendAPI coordina ambos servicios.
- Pantalla completa cuando el navegador la admite. Recursos del jurado en el cierre.
- La vista 05 presenta ocho contribuciones destacadas y una fila de colaboradores, con los LinkedIn proporcionados. Los avatares muestran iniciales hasta disponer de fotos autorizadas. Davo Ruiz y Óscar Muñoz no tienen enlace porque no se proporcionaron sus perfiles.
- Sin JavaScript se muestran las seis vistas en secuencia con el diagrama estático y acceso al producto y repositorio. Las animaciones respetan `prefers-reduced-motion`.

La arquitectura es una explicación visual del proyecto, no una simulación conectada a los servicios. El ciclo finaliza al aprobar el contenido o llegar al límite de correcciones; no representa una aprobación garantizada.

## Estética y fuentes

Fondos `#090c10`, `#121822` y `#1a2230`; acentos cian, azul, violeta y dorado tomados del sistema visual del frontend. Tipografía local, sin fuentes remotas. Las relaciones de los diagramas se reconstruyen en SVG.

Fuente principal: `docs/README_Panorama_Pitch_DemoDay_NuevaMente.md`. Arquitectura y flujos: diagramas de Sprint 4 y ciclo de evaluación de `docs/`. Se mantiene la premisa acordada de producto implementado. No se inventan métricas ni nombres de integrantes.

## Servir

Abrir `index.html` directamente, o desde la raíz:

```powershell
python -m http.server 8080 --directory landing
```

Para Nginx, copiar esta carpeta a una raíz estática independiente:

```nginx
server {
    listen 80;
    server_name landing.example.com;
    root /var/www/nuevamente-landing;
    index index.html;
    location / {
        try_files $uri $uri/ =404;
    }
}
```

Configurar dominio y HTTPS en infraestructura. No necesita proxy ni fallback SPA. Los recursos usan rutas relativas y permiten servir bajo un subdirectorio.

Los enlaces de producto en `index.html` usan `http://155.181.154.104/`, según el diagrama OCI. Actualizarlos si cambia la dirección. Los archivos en `assets/` son copias independientes del panorama y los diagramas para consulta posterior; deben actualizarse si cambian los originales. No se modifican archivos del frontend principal.
