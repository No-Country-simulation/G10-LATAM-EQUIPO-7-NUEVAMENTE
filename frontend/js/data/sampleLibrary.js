/**
 * sampleLibrary.js
 * Catálogo de 10 Libros de Estudio Multidisciplinarios para el Gran Librero de NuevaMente.
 * Cada libro representa un documento técnico / educativo completamente interactivo.
 */

export const sampleLibrary = {
  // 1. Tecnología
  "cloud_architecture": {
    id: "sample_cloud",
    filename: "Arquitectura Cloud & Microservicios.pdf",
    discipline: "Ingeniería de Software",
    title: "Arquitectura Cloud Nativa & Microservicios",
    description: "Patrones de diseño desacoplados, escalabilidad horizontal, contenedores y balanceo de carga en la nube.",
    filesize: "3.2 MB",
    spineColor: "navy",
    icon: "☁️",
    metadatos: {
      perfil: "intermedio",
      nivel_detalle: "equilibrado",
      tiempo_estudio: "12 min",
      anclaje_rag: 99.4,
      fidelidad: "Alta (Verificada)",
      chunks_count: 18
    },
    sections: [
      {
        id: "sec_load_balancing",
        title: "Balanceo de Carga & Escalabilidad",
        summary: "Mecanismos para distribuir solicitudes en Layer 4 y Layer 7 entre réplicas sin estado para evitar puntos únicos de fallo.",
        key_concepts: ["Reverse Proxy", "Health Checks", "Round Robin", "Auto-scaling"],
        flashcards: [
          {
            frente: "¿Cuál es el rol crítico de un Reverse Proxy en arquitectura Cloud?",
            dorso: "Intermediar entre clientes externos y microservicios internos, realizando terminación SSL, enrutamiento y balanceo de tráfico.",
            pista_didactica: "Actúa como un recepcionista de hotel que guía a cada huésped a su habitación sin exponer las oficinas internas."
          },
          {
            frente: "¿Qué diferencia al escalado horizontal del vertical?",
            dorso: "El horizontal agrega más réplicas en paralelo; el vertical añade más recursos (RAM/CPU) al mismo servidor.",
            pista_didactica: "Contratar más cocineros vs. pedirle a un solo cocinero que cocine 10 veces más rápido."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "La computación en la nube prioriza sistemas resilientes donde los servicios son efímeros y reemplazables. El balanceo de carga continuo garantiza alta disponibilidad.",
          puntos_clave: [
            "Desacoplamiento total entre el estado de la sesión y las instancias de cómputo.",
            "Supervisión activa de salud (Liveness y Readiness probes).",
            "Mitigación automática de sobrecargas mediante auto-scaling elástico."
          ],
          terminos_clave: ["High Availability", "Failover", "Load Balancer", "Stateless"]
        },
        video: {
          titulo_video: "Diseño de Microservicios de Alta Disponibilidad",
          duracion: "4:45 min",
          puntos_video: [
            "Min 0:40 - Diagnóstico de cuellos de botella en APIs monolíticas.",
            "Min 2:10 - Configuración de clústeres redundantes con OCI / Kubernetes.",
            "Min 3:50 - Estrategias de despliegue Zero-Downtime (Blue/Green)."
          ]
        },
        quiz: {
          pregunta: "¿Por qué se prefieren servicios 'stateless' (sin estado) en entornos de escalado dinámico en la nube?",
          opciones: [
            "Porque consumen menos espacio en disco duro local.",
            "Porque cualquier instancia puede atender cualquier solicitud sin depender de memoria previa.",
            "Porque impiden que el usuario envíe peticiones POST al servidor.",
            "Porque eliminan por completo la necesidad de bases de datos."
          ],
          correcta: 1,
          explicacion: "Al no retener estado en el servidor web, el balanceador puede redirigir las peticiones a cualquier réplica disponible instantáneamente."
        }
      }
    ]
  },

  // 2. Ciencias Médicas
  "neuroscience_learning": {
    id: "sample_neuro",
    filename: "Fundamentos de Neurobiología del Aprendizaje.pdf",
    discipline: "Neurociencias & Medicina",
    title: "Neurobiología y Mecanismos de la Memoria",
    description: "Bases sinápticas de la plasticidad neuronal, potenciación a largo plazo (LTP) y retención mnemotécnica.",
    filesize: "4.1 MB",
    spineColor: "emerald",
    icon: "🧠",
    metadatos: {
      perfil: "principiante",
      nivel_detalle: "conceptual",
      tiempo_estudio: "10 min",
      anclaje_rag: 99.8,
      fidelidad: "Alta (Verificada)",
      chunks_count: 22
    },
    sections: [
      {
        id: "sec_plasticity",
        title: "Plasticidad Sináptica y Memoria Duradera",
        summary: "Capacidad del sistema nervioso para modificar la fuerza de sus conexiones neuronales en respuesta a la estimulación repetida.",
        key_concepts: ["Sinapsis", "LTP", "Neurotransmisores", "Glutamato"],
        flashcards: [
          {
            frente: "¿Qué es la Potenciación a Largo Plazo (LTP)?",
            dorso: "Es el fortalecimiento persistente de las sinapsis basado en patrones recientes de actividad, base celular de la memoria.",
            pista_didactica: "Piensa en un sendero en el pasto: cuanto más se camina por él, más fácil de transitar se vuelve."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "El cerebro humano no es estático; se reconfigura constantemente mediante repetición espaciada y recuerdo activo.",
          puntos_clave: [
            "La repetición espaciada induce síntesis de nuevas proteínas sinápticas.",
            "El sueño profundo consolida recuerdos en la corteza cerebral."
          ],
          terminos_clave: ["Neuroplasticidad", "Receptores NMDA", "Hipocampo"]
        },
        video: {
          titulo_video: "Viaje al interior de la sinapsis humana",
          duracion: "3:50 min",
          puntos_video: [
            "Min 0:30 - Anatomía del axón y la hendidura sináptica.",
            "Min 1:50 - Entrada de iones de calcio y cascadas enzimáticas."
          ]
        },
        quiz: {
          pregunta: "¿Cuál es la estructura cerebral primordial para la consolidación inicial de recuerdos declarativos?",
          opciones: ["El cerebelo", "El hipocampo", "La médula espinal", "El lóbulo occipital"],
          correcta: 1,
          explicacion: "El hipocampo actúa como el índice central que coordina la integración y posterior almacenamiento cortical."
        }
      }
    ]
  },

  // 3. Leyes & Privacidad
  "legal_dataprotection": {
    id: "sample_legal",
    filename: "Derecho Digital & Protección de Datos.docx",
    discipline: "Derecho & Ciberseguridad",
    title: "Regulación de Privacidad & Protección de Datos",
    description: "Principios jurídicos fundamentales del RGPD y normativas sobre tratamiento ético de datos personales.",
    filesize: "1.9 MB",
    spineColor: "burgundy",
    icon: "⚖️",
    metadatos: {
      perfil: "avanzado",
      nivel_detalle: "profundo",
      tiempo_estudio: "9 min",
      anclaje_rag: 99.1,
      fidelidad: "Alta (Verificada)",
      chunks_count: 15
    },
    sections: [
      {
        id: "sec_gdpr_principles",
        title: "Principios de Tratamiento y Consentimiento",
        summary: "Licitud, lealtad, limitación de la finalidad y minimización de datos en el ciclo de vida del software moderno.",
        key_concepts: ["Minimización", "Consentimiento Explícito", "Habeas Data", "DPO"],
        flashcards: [
          {
            frente: "¿En qué consiste el principio de 'Minimización de Datos'?",
            dorso: "Obliga a recolectar únicamente los datos estrictamente necesarios para la finalidad específica declarada.",
            pista_didactica: "Si una app de linterna te pide tu ubicación y contactos, está violando este principio."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "La privacidad por diseño exige que las salvaguardas de datos se integren desde la fase de arquitectura técnica.",
          puntos_clave: ["Consentimiento libre y específico", "Notificación de brechas en <72h", "Responsabilidad proactiva."],
          terminos_clave: ["Privacy by Design", "RGPD", "Minimización"]
        },
        video: {
          titulo_video: "Compliance Legal para Desarrolladores y Startups",
          duracion: "4:15 min",
          puntos_video: ["Min 0:50 - Qué califica como Dato Sensible.", "Min 2:15 - Cifrado obligatorio."]
        },
        quiz: {
          pregunta: "¿Qué principio exige incorporar salvaguardas de privacidad desde la concepción del sistema?",
          opciones: ["Privacy by Design", "In dubio pro reo", "Publicidad Procesal", "Autonomía de la Voluntad"],
          correcta: 0,
          explicacion: "Privacy by Design establece que la protección debe ser inherente a la arquitectura técnica."
        }
      }
    ]
  },

  // 4. Economía & Finanzas
  "behavioral_economics": {
    id: "sample_econ",
    filename: "Economía del Comportamiento & Finanzas.pdf",
    discipline: "Economía & Negocios",
    title: "Economía del Comportamiento y Toma de Decisiones",
    description: "Sesgos cognitivos, teoría de perspectivas (Prospect Theory) y arquitectura de decisiones financieras.",
    filesize: "2.7 MB",
    spineColor: "amber",
    icon: "📈",
    metadatos: {
      perfil: "intermedio",
      nivel_detalle: "equilibrado",
      tiempo_estudio: "11 min",
      anclaje_rag: 99.0,
      fidelidad: "Alta",
      chunks_count: 17
    },
    sections: [
      {
        id: "sec_biases",
        title: "Aversión a las Pérdidas y Efecto Señuelo",
        summary: "Cómo las asimetrías psicológicas entre pérdidas y ganancias condicionan las elecciones del inversor.",
        key_concepts: ["Loss Aversion", "Nudge", "Heurística", "Anclaje"],
        flashcards: [
          {
            frente: "¿Qué postula el principio de 'Aversión a la Pérdida' de Kahneman?",
            dorso: "El dolor psicológico de perder \$100 es aproximadamente el doble de intenso que la alegría de ganar \$100.",
            pista_didactica: "Preferimos evitar un golpe antes que recibir un abrazo de igual magnitud."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "La economía conductual demuestra que los agentes económicos no son perfectamente racionales, sino influenciados por atajos mentales heurísticos.",
          puntos_clave: ["Asimetría emocional pérdida/ganancia", "Importancia del marco de referencia (Framing)"],
          terminos_clave: ["Prospect Theory", "Nudge", "Framing"]
        },
        video: {
          titulo_video: "Psicología del Dinero: Por qué tomamos malas decisiones",
          duracion: "5:10 min",
          puntos_video: ["Min 1:00 - El sesgo del costo hundido.", "Min 3:20 - Arquitectura de elecciones (Nudge)."]
        },
        quiz: {
          pregunta: "¿Cómo se denomina al impulso de mantener una inversión perdedora solo por el tiempo o dinero ya invertido?",
          opciones: ["Falacia del costo hundido", "Efecto anclaje", "Sesgo de confirmación", "Teoría del cisne negro"],
          correcta: 0,
          explicacion: "La falacia del costo hundido lleva a persistir en un error para justificar el gasto previo no recuperable."
        }
      }
    ]
  },

  // 5. Inteligencia Artificial
  "deep_learning_rag": {
    id: "sample_ai",
    filename: "Inteligencia Artificial & Deep Learning.pdf",
    discipline: "Inteligencia Artificial",
    title: "Arquitectura de Transformers y Sistemas RAG",
    description: "Atención autorregresiva, embeddings vectoriales, búsqueda semántica y recuperación aumentada por generación.",
    filesize: "3.8 MB",
    spineColor: "purple",
    icon: "🤖",
    metadatos: {
      perfil: "avanzado",
      nivel_detalle: "profundo",
      tiempo_estudio: "14 min",
      anclaje_rag: 99.6,
      fidelidad: "Verificada por Agente Crítico",
      chunks_count: 24
    },
    sections: [
      {
        id: "sec_rag_arch",
        title: "Retrieval-Augmented Generation (RAG)",
        summary: "Patrón de arquitectura que ancla respuestas generativas a fuentes de conocimiento privadas o externas.",
        key_concepts: ["Vector DB", "Cosine Similarity", "Top-K", "Hallucination Mitigation"],
        flashcards: [
          {
            frente: "¿Por qué RAG reduce drásticamente las alucinaciones en los LLMs?",
            dorso: "Porque obliga al modelo a redactar su respuesta usando exclusivamente los fragmentos (chunks) recuperados del documento original.",
            pista_didactica: "Es como rendir un examen 'a libro abierto': consultas la página exacta en vez de inventar de memoria."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "RAG desacopla el razonamiento del LLM de su memoria estática, permitiendo auditoría de fuentes y fidelidad matemática del 99%.",
          puntos_clave: ["Búsqueda vectorial en ChromaDB", "Recuperación semántica densa", "Evaluación de fidelidad con agente crítico"],
          terminos_clave: ["RAG", "Embeddings", "Cosine Similarity", "ChromaDB"]
        },
        video: {
          titulo_video: "Construyendo un Pipeline RAG de Grado de Producción",
          duracion: "6:00 min",
          puntos_video: ["Min 1:15 - Chunking semántico.", "Min 3:30 - Indexación de vectores.", "Min 4:50 - Agente evaluador."]
        },
        quiz: {
          pregunta: "¿Qué métrica matemática se utiliza habitualmente para comparar la proximidad semántica entre dos vectores de embedding?",
          opciones: ["Similitud del Coseno", "Derivada Parcial", "Algoritmo de Dijkstra", "Regresión Lineal Simple"],
          correcta: 0,
          explicacion: "La similitud del coseno mide el ángulo entre dos vectores normalizados en el espacio semántico multidimensional."
        }
      }
    ]
  },

  // 6. Bioquímica & Genética
  "molecular_genetics": {
    id: "sample_genetics",
    filename: "Bioquímica Celular & Genética Molecular.pdf",
    discipline: "Biología & Genética",
    title: "Mecanismos de Transcripción y Edición Genética CRISPR",
    description: "Dogma central de la biología molecular, ARN mensajero, ribosomas y edición de precisión con Cas9.",
    filesize: "4.5 MB",
    spineColor: "forest",
    icon: "🧬",
    metadatos: {
      perfil: "intermedio",
      nivel_detalle: "equilibrado",
      tiempo_estudio: "13 min",
      anclaje_rag: 99.5,
      fidelidad: "Alta",
      chunks_count: 20
    },
    sections: [
      {
        id: "sec_crispr",
        title: "El Sistema CRISPR-Cas9 y Reparación del ADN",
        summary: "Endonucleasas guiadas por ARN que generan cortes de doble cadena dirigidos para terapia génica.",
        key_concepts: ["ARN guía", "Cas9", "PAM", "Reparación Homóloga"],
        flashcards: [
          {
            frente: "¿Cuál es la función del ARN Guía (gRNA) en el complejo CRISPR-Cas9?",
            dorso: "Hibridar con la secuencia de ADN complementaria exacta para posicionar la enzima Cas9 en el punto de corte deseado.",
            pista_didactica: "Es las coordenadas GPS que le indican a la tijera molecular dónde debe cortar."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "CRISPR revolucionó la ingeniería genética al permitir edición de nucleótidos específicos con precisión molecular inaudita.",
          puntos_clave: ["Corte en secuencias específicas", "Mecanismos de inserción y deleción"],
          terminos_clave: ["CRISPR", "Cas9", "Mutagénesis", "Gentrash"]
        },
        video: {
          titulo_video: "Cómo funciona la tijera molecular CRISPR",
          duracion: "4:30 min",
          puntos_video: ["Min 1:00 - El origen bacteriano de CRISPR.", "Min 3:00 - La aplicación en medicina moderna."]
        },
        quiz: {
          pregunta: "¿Qué componente de CRISPR realiza el corte físico en las dos hebras del ADN?",
          opciones: ["La enzima Cas9", "El ARN mensajero", "El ribosoma 80S", "La polimerasa Taq"],
          correcta: 0,
          explicacion: "Cas9 es la proteína endonucleasa responsable de efectuar el corte bicatenario en el ADN."
        }
      }
    ]
  },

  // 7. Ciberseguridad & Criptografía
  "cybersecurity_crypto": {
    id: "sample_crypto",
    filename: "Ciberseguridad & Criptografía Aplicada.pdf",
    discipline: "Ciberseguridad",
    title: "Criptografía de Clave Pública y Seguridad Zero Trust",
    description: "Algoritmos asimétricos (RSA, ECC), funciones hash (SHA-256), firmas digitales y modelos de confianza cero.",
    filesize: "2.9 MB",
    spineColor: "slate",
    icon: "🛡️",
    metadatos: {
      perfil: "avanzado",
      nivel_detalle: "profundo",
      tiempo_estudio: "12 min",
      anclaje_rag: 99.3,
      fidelidad: "Alta",
      chunks_count: 19
    },
    sections: [
      {
        id: "sec_zero_trust",
        title: "Arquitectura Zero Trust y Cifrado Asimétrico",
        summary: "Principio de 'nunca confiar, siempre verificar' aplicado a identidades, microperímetros y canales cifrados.",
        key_concepts: ["Zero Trust", "RSA", "Diffie-Hellman", "MFA"],
        flashcards: [
          {
            frente: "¿En qué se diferencia el cifrado asimétrico del simétrico?",
            dorso: "El asimétrico usa un par de claves (pública para cifrar, privada para descifrar); el simétrico usa la misma clave para ambas acciones.",
            pista_didactica: "Un candado abierto que cualquiera puede cerrar con su mano, pero solo tú tienes la llave para abrirlo."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "Zero Trust reemplaza la seguridad perimetral tradicional por autenticación continua de contexto en cada solicitud.",
          puntos_clave: ["Principio de mínimo privilegio", "Microsegmentación de red", "Cifrado de extremo a extremo"],
          terminos_clave: ["Zero Trust", "MFA", "PKI", "SHA-256"]
        },
        video: {
          titulo_video: "Implementación de Zero Trust en Arquitecturas Modernas",
          duracion: "5:00 min",
          puntos_video: ["Min 1:10 - La caída del modelo perimetral.", "Min 3:25 - Gestión de identidades federadas."]
        },
        quiz: {
          pregunta: "¿Qué premisa define el modelo de seguridad Zero Trust?",
          opciones: ["Nunca confiar, siempre verificar continuamente", "Confiar en todos los dispositivos de la red interna", "Desactivar la autenticación de dos factores", "Permitir accesos de administrador sin registro"],
          correcta: 0,
          explicacion: "Zero Trust asume que las amenazas ya están dentro de la red y valida cada petición independientemente de su origen."
        }
      }
    ]
  },

  // 8. Historia de la Ciencia
  "scientific_revolutions": {
    id: "sample_history",
    filename: "Historia de las Revoluciones Científicas.pdf",
    discipline: "Humanidades & Filosofía",
    title: "Estructura de las Revoluciones Científicas",
    description: "Paradigmas, ciencia normal y cambios de cosmovisión desde Copérnico hasta la teoría de la relatividad.",
    filesize: "3.1 MB",
    spineColor: "ruby",
    icon: "🏛️",
    metadatos: {
      perfil: "principiante",
      nivel_detalle: "conceptual",
      tiempo_estudio: "10 min",
      anclaje_rag: 99.7,
      fidelidad: "Alta",
      chunks_count: 16
    },
    sections: [
      {
        id: "sec_kuhn_paradigms",
        title: "Thomas Kuhn y el Concepto de Paradigma",
        summary: "Cómo la ciencia progresa no de manera lineal continua, sino a través de rupturas revolucionarias periódicas.",
        key_concepts: ["Paradigma", "Ciencia Normal", "Anomalías", "Crisis"],
        flashcards: [
          {
            frente: "¿Qué es un 'Cambio de Paradigma' según Thomas Kuhn?",
            dorso: "Es una transformación radical en el marco teórico y metodológico con el que una comunidad científica interpreta el mundo.",
            pista_didactica: "Cambiar los anteojos con los que miras el universo por unos de aumento totalmente diferente."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "La ciencia atraviesa períodos estables de 'ciencia normal' hasta que las anomalías acumuladas fuerzan una revolución conceptual.",
          puntos_clave: ["Acumulación de anomalías", "Inconmensurabilidad entre paradigmas"],
          terminos_clave: ["Kuhn", "Epistemología", "Revolución"]
        },
        video: {
          titulo_video: "De Copérnico a Einstein: Las Grandes Rupturas",
          duracion: "4:40 min",
          puntos_video: ["Min 1:00 - El geocentrismo y su crisis.", "Min 3:15 - El nacimiento de la física cuántica."]
        },
        quiz: {
          pregunta: "¿Qué autor acuñó el término 'cambio de paradigma' en su obra de 1962?",
          opciones: ["Thomas Kuhn", "Karl Popper", "René Descartes", "Francis Bacon"],
          correcta: 0,
          explicacion: "Thomas Kuhn introdujo el concepto en 'La estructura de las revoluciones científicas'."
        }
      }
    ]
  },

  // 9. Psicología Cognitiva
  "cognitive_psychology": {
    id: "sample_psych",
    filename: "Psicología Cognitiva & Memoria Humana.pdf",
    discipline: "Psicología & Neurociencia",
    title: "Procesamiento de Información y Carga Cognitiva",
    description: "Memoria de trabajo, efecto de espaciamiento, teoría de la carga cognitiva y estrategias de metacognición.",
    filesize: "2.5 MB",
    spineColor: "indigo",
    icon: "🧩",
    metadatos: {
      perfil: "intermedio",
      nivel_detalle: "equilibrado",
      tiempo_estudio: "11 min",
      anclaje_rag: 99.2,
      fidelidad: "Alta",
      chunks_count: 18
    },
    sections: [
      {
        id: "sec_working_memory",
        title: "La Memoria de Trabajo y el Efecto de Espaciado",
        summary: "Limitaciones del bucle fonológico y la agenda visoespacial, y cómo el repaso espaciado vence la curva del olvido.",
        key_concepts: ["Memoria de Trabajo", "Curva del Olvido", "Ebbinghaus", "Metacognición"],
        flashcards: [
          {
            frente: "¿Qué demostró Hermann Ebbinghaus con la 'Curva del Olvido'?",
            dorso: "Que olvidamos más del 50% de la información aprendida dentro de las primeras 24 horas a menos que realicemos un repaso activo espaciado.",
            pista_didactica: "Una fuga en un tanque de agua: si no sellas la fuga con repasos periódicos, el tanque se vacía rápidamente."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "La memoria de trabajo humana tiene capacidad limitada (4-7 elementos simultáneos). Las técnicas de fragmentación (chunking) y las flashcards optimizan la retención.",
          puntos_clave: ["Evitar sobrecarga cognitiva", "Repaso activo espaciado", "Consolidación a largo plazo"],
          terminos_clave: ["Chunking", "Curva del Olvido", "Metacognición"]
        },
        video: {
          titulo_video: "Estrategias de Aprendizaje Acelerado con Base Científica",
          duracion: "4:50 min",
          puntos_video: ["Min 1:10 - Los límites de la memoria de trabajo.", "Min 3:00 - Por qué releer no sirve y el recuerdo activo sí."]
        },
        quiz: {
          pregunta: "¿Cuál de los siguientes métodos de estudio tiene mayor evidencia científica de retención duradera?",
          opciones: ["La recuperación activa y repetición espaciada (Flashcards)", "Releer pasivamente el texto subrayado", "Estudiar 10 horas seguidas la noche anterior", "Escuchar grabaciones de audio mientras duermes"],
          correcta: 0,
          explicacion: "El esfuerzo activo por recuperar información de la memoria (Active Recall) fortalece físicamente las vías sinápticas."
        }
      }
    ]
  },

  // 10. Física Cuántica
  "quantum_physics": {
    id: "sample_quantum",
    filename: "Física Cuántica para Curiosos.pdf",
    discipline: "Física & Ciencias Exactas",
    title: "Principios Fundamentales de la Mecánica Cuántica",
    description: "Dualidad onda-partícula, superposición, entrelazamiento cuántico y el principio de incertidumbre de Heisenberg.",
    filesize: "3.4 MB",
    spineColor: "cyan",
    icon: "⚛️",
    metadatos: {
      perfil: "principiante",
      nivel_detalle: "conceptual",
      tiempo_estudio: "12 min",
      anclaje_rag: 99.4,
      fidelidad: "Alta",
      chunks_count: 21
    },
    sections: [
      {
        id: "sec_superposition",
        title: "Superposición Cuántica y Dualidad Onda-Partícula",
        summary: "El comportamiento probabilístico de partículas subatómicas y el experimento de la doble rendija.",
        key_concepts: ["Superposición", "Función de Onda", "Heisenberg", "Colapso"],
        flashcards: [
          {
            frente: "¿Qué postula el Principio de Incertidumbre de Heisenberg?",
            dorso: "Es imposible conocer simultáneamente y con precisión arbitraria la posición y el momento lineal (velocidad) de una partícula.",
            pista_didactica: "Cuanto más intentas fijar dónde está algo diminuto, menos sabes hacia dónde se mueve."
          }
        ],
        sintesis: {
          resumen_ejecutivo: "En la escala atómica, la materia no sigue leyes deterministas clásicas sino estados superpuestos descritos por funciones de onda de probabilidad.",
          puntos_clave: ["Dualidad onda-corpúsculo", "El acto de medición colapsa la función de onda"],
          terminos_clave: ["Superposición", "Heisenberg", "Función de Onda"]
        },
        video: {
          titulo_video: "El Experimento de la Doble Rendija Explicado",
          duracion: "5:20 min",
          puntos_video: ["Min 1:00 - Ondas vs Partículas.", "Min 3:15 - El misterioso colapso del observador."]
        },
        quiz: {
          pregunta: "¿Qué fenómeno describe partículas cuyas propiedades permanecen interconectadas sin importar la distancia entre ellas?",
          opciones: ["Entrelazamiento Cuántico", "Radiación de Fondo", "Efecto Doppler", "Refracción Óptica"],
          correcta: 0,
          explicacion: "El entrelazamiento cuántico (lo que Einstein llamaba 'acción fantasmal a la distancia') vincula estados cuánticos al instante."
        }
      }
    ]
  }
};
