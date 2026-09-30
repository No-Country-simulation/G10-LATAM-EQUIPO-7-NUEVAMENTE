/**
 * showcaseWorlds.js
 * Mundos de estudio multidisciplinarios de demostración para el Sistema Solar y el Catálogo.
 * Permite explorar y probar toda la experiencia visual e interactiva cuando el backend
 * aún no tiene documentos cargados o se ejecuta en modo de demostración.
 */

export const showcaseWorlds = [
  {
    id: "world_cloud",
    title: "Arquitectura Cloud & Microservicios",
    filename: "Arquitectura_Cloud_Microservicios.pdf",
    discipline: "Ingeniería de Software",
    spineColor: "cyan",
    description: "Principios de diseño desacoplado, escalabilidad horizontal, contenedores Docker y orquestación resiliente con Kubernetes.",
    filesize: "2.8 MB",
    status: "stored",
    metadatos: {
      document_id: "world_cloud",
      tiempo_estudio: "12 min",
      perfil: "intermediate",
      formato: "PDF"
    },
    sections: [
      {
        id: "sec_cloud_1",
        title: "Microservicios y Alta Disponibilidad",
        summary: "Fundamentos de diseño de servicios autónomos con tolerancia a fallas, balanceo de carga y comunicación orientada a eventos.",
        key_concepts: ["Microservicios", "Kubernetes", "Idempotencia", "Circuit Breaker"],
        flashcards: [
          {
            front: "¿Qué es la idempotencia en una API REST?",
            back: "Es la propiedad por la cual realizar la misma solicitud varias veces produce el mismo resultado sin efectos secundarios adicionales.",
            didactic_hint: "Pensá en el método HTTP PUT o DELETE vs POST."
          },
          {
            front: "¿Qué diferencia a la escalabilidad horizontal de la vertical?",
            back: "La horizontal suma más instancias/nodos a un cluster; la vertical aumenta CPU y RAM a un mismo servidor físico o virtual.",
            didactic_hint: "Scaling out vs Scaling up."
          },
          {
            front: "¿Qué patrón de diseño previene la cascada de fallas en microservicios?",
            back: "El patrón Circuit Breaker (Disyuntor), aislando temporalmente servicios lentos o caídos para evitar agotar recursos del llamador.",
            didactic_hint: "Funciona igual que una llave térmica en una casa."
          }
        ],
        quiz: {
          question: "¿Cuál es la principal ventaja de desacoplar servicios mediante colas de mensajería asíncronas?",
          options: [
            "Aumentar deliberadamente la latencia entre procesos",
            "Tolerancia a fallas y absorción de picos de carga imprevistos",
            "Eliminar por completo la necesidad de bases de datos",
            "Evitar escribir pruebas automatizadas"
          ],
          correct_answer: 1,
          explanation: "Las colas asíncronas permiten que productores y consumidores operen a su propio ritmo, garantizando que un pico de tráfico no derribe el sistema."
        }
      }
    ]
  },
  {
    id: "world_neuro",
    title: "Neurobiología del Aprendizaje & Memoria",
    filename: "Neurobiologia_del_Aprendizaje.pdf",
    discipline: "Ciencias Médicas & Biología",
    spineColor: "ruby",
    description: "Mecanismos sinápticos de consolidación de memoria a largo plazo, potenciación a largo plazo (LTP) y plasticidad celular.",
    filesize: "3.4 MB",
    status: "stored",
    metadatos: {
      document_id: "world_neuro",
      tiempo_estudio: "15 min",
      perfil: "advanced",
      formato: "PDF"
    },
    sections: [
      {
        id: "sec_neuro_1",
        title: "Potenciación a Largo Plazo (LTP)",
        summary: "Bases moleculares de la plasticidad sináptica en el hipocampo y cómo la repetición espaciada refuerza las conexiones neuronales.",
        key_concepts: ["Neuroplasticidad", "Sinapsis", "Receptores NMDA", "Hipocampo"],
        flashcards: [
          {
            front: "¿Qué estructura cerebral es esencial para consolidar la memoria episódica?",
            back: "El hipocampo, el cual actúa como puente antes de que los recuerdos se transfieran a la neocorteza.",
            didactic_hint: "Estructura con forma de caballito de mar en el lóbulo temporal."
          },
          {
            front: "¿Qué neurotransmisor es el principal mediador de la plasticidad sináptica excitatoria?",
            back: "El glutamato, a través de los receptores NMDA y AMPA.",
            didactic_hint: "El aminoácido excitatorio más abundante del sistema nervioso central."
          }
        ],
        quiz: {
          question: "¿Qué fenómeno celular sustenta la formación de recuerdos duraderos?",
          options: [
            "La necrosis neuronal programada",
            "La potenciación a largo plazo (LTP) mediada por sinapsis",
            "El cese de la actividad de los canales de calcio",
            "La desmielinización axónica rápida"
          ],
          correct_answer: 1,
          explanation: "La LTP incrementa la fuerza sináptica entre neuronas estimuladas concurrentemente, base neurobiológica de la memoria."
        }
      }
    ]
  },
  {
    id: "world_ai",
    title: "Modelos de Lenguaje & Arquitectura Transformer",
    filename: "Modelos_Lenguaje_Transformers.pdf",
    discipline: "Inteligencia Artificial",
    spineColor: "purple",
    description: "Mecanismo de auto-atención multi-cabezal, embeddings vectoriales y generación aumentada por recuperación (RAG).",
    filesize: "4.1 MB",
    status: "stored",
    metadatos: {
      document_id: "world_ai",
      tiempo_estudio: "10 min",
      perfil: "intermediate",
      formato: "PDF"
    },
    sections: [
      {
        id: "sec_ai_1",
        title: "Atención Multi-Cabezal y Embeddings",
        summary: "Cómo los transformers ponderan relaciones entre palabras a cualquier distancia sin recurrencia secuencial.",
        key_concepts: ["Self-Attention", "Embeddings", "RAG Pipeline", "Vector DB"],
        flashcards: [
          {
            front: "¿Qué resuelven los embeddings vectoriales en PLN?",
            back: "Capturan la cercanía y similitud semántica de palabras y frases mapeándolas a un espacio numérico denso multidimensional.",
            didactic_hint: "Permite medir distancia angular o coseno entre conceptos afines."
          },
          {
            front: "¿Cuál es el propósito central del patrón RAG (Retrieval-Augmented Generation)?",
            back: "Conectar un modelo de lenguaje generativo con fuentes documentales externas actualizadas para fundamentar sus respuestas y mitigar alucinaciones.",
            didactic_hint: "Recuperar contexto verificado antes de generar la respuesta."
          }
        ],
        quiz: {
          question: "¿Por qué la auto-atención (Self-Attention) superó a las redes recurrentes tradicionales (RNNs)?",
          options: [
            "Porque solo puede procesar una palabra a la vez",
            "Porque permite procesamiento masivamente paralelo y retiene contexto a larga distancia",
            "Porque no requiere entrenamiento matemático",
            "Porque únicamente sirve para traducir idiomas antiguos"
          ],
          correct_answer: 1,
          explanation: "Al eliminar la dependencia secuencial estricta paso a paso, los Transformers procesan secuencias completas en paralelo en GPU."
        }
      }
    ]
  },
  {
    id: "world_legal",
    title: "Derecho Digital & Privacidad de Datos",
    filename: "Derecho_Digital_Proteccion_Datos.docx",
    discipline: "Ciencias Jurídicas & Derecho",
    spineColor: "amber",
    description: "Regulaciones de privacidad (GDPR, LPDP), consentimiento informado, responsabilidad algorítmica y ciberseguridad jurídica.",
    filesize: "1.9 MB",
    status: "stored",
    metadatos: {
      document_id: "world_legal",
      tiempo_estudio: "8 min",
      perfil: "intermediate",
      formato: "DOCX"
    },
    sections: [
      {
        id: "sec_legal_1",
        title: "Marco Regulatorio y Soberanía de Datos",
        summary: "Principios rectores de licitud, lealtad y minimización en el tratamiento automatizado de datos personales.",
        key_concepts: ["GDPR", "Minimización", "Derecho al Olvido", "Compliance"],
        flashcards: [
          {
            front: "¿En qué consiste el principio de 'Minimización de Datos'?",
            back: "Los datos recopilados deben ser adecuados, pertinentes y limitados estrictamente a lo necesario para los fines declarados.",
            didactic_hint: "No solicitar datos superfluos que no hacen al objetivo del servicio."
          }
        ],
        quiz: {
          question: "¿Qué requisito fundamental exige el GDPR para considerar válido el consentimiento del usuario?",
          options: [
            "Que esté implícito en casillas pre-marcadas por defecto",
            "Que sea libre, específico, informado e inequívoco mediante una acción afirmativa clara",
            "Que se renueve automáticamente cada 24 horas",
            "Que solo aplique a mayores de 65 años"
          ],
          correct_answer: 1,
          explanation: "El consentimiento no puede ser tácito ni forzado; requiere una manifestación de voluntad explícita."
        }
      }
    ]
  },
  {
    id: "world_econ",
    title: "Economía de Plataformas & Mercados Digitales",
    filename: "Economia_Plataformas_Mercados.pdf",
    discipline: "Economía & Negocios",
    spineColor: "emerald",
    description: "Efectos de red directos e indirectos, fijación de precios en mercados bilaterales y dinámicas de monopolios naturales digitales.",
    filesize: "2.1 MB",
    status: "stored",
    metadatos: {
      document_id: "world_econ",
      tiempo_estudio: "9 min",
      perfil: "intermediate",
      formato: "PDF"
    },
    sections: [
      {
        id: "sec_econ_1",
        title: "Efectos de Red y Mercados Bilaterales",
        summary: "Cómo el valor de una plataforma se incrementa exponencialmente con cada nuevo participante en ambos lados del mercado.",
        key_concepts: ["Efectos de Red", "Mercados Bilaterales", "Costos de Cambio", "Economías de Escala"],
        flashcards: [
          {
            front: "¿Qué es un efecto de red indirecto?",
            back: "Ocurre cuando el aumento de usuarios de un tipo (ej. compradores) atrae a más usuarios de otro tipo complementario (ej. vendedores).",
            didactic_hint: "La dinámica clásica de marketplaces como MercadoLibre o Airbnb."
          }
        ],
        quiz: {
          question: "¿Qué suele ocurrir en mercados con fortísimos efectos de red y altos costos de cambio?",
          options: [
            "Todos los competidores tienen idéntica cuota de mercado",
            "Una dinámica 'Winner-Take-Most' donde una sola plataforma domina el mercado",
            "La desaparición del dinero electrónico",
            "Una caída inmediata de los usuarios"
          ],
          correct_answer: 1,
          explanation: "Los efectos de red generan una espiral positiva para el líder, dificultando la entrada de nuevos competidores."
        }
      }
    ]
  },
  {
    id: "world_phil",
    title: "Filosofía de la Mente & Epistemología",
    filename: "Filosofia_de_la_Mente.pdf",
    discipline: "Humanidades & Filosofía",
    spineColor: "sapphire",
    description: "El problema mente-cuerpo, el problema difícil de la conciencia de Chalmers, experimentos mentales y cognición artificial.",
    filesize: "1.7 MB",
    status: "stored",
    metadatos: {
      document_id: "world_phil",
      tiempo_estudio: "11 min",
      perfil: "advanced",
      formato: "PDF"
    },
    sections: [
      {
        id: "sec_phil_1",
        title: "El Problema Difícil de la Conciencia",
        summary: "Análisis de por qué y cómo los procesos físicos y computacionales dan origen a la experiencia subjetiva (Qualia).",
        key_concepts: ["Qualia", "Dualismo", "Habitación China", "Funcionalismo"],
        flashcards: [
          {
            front: "¿Qué busca demostrar el experimento mental de la 'Habitación China' de John Searle?",
            back: "Que la mera manipulación sintáctica de símbolos según reglas lógicas no equivale a una comprensión semántica o conciencia real.",
            didactic_hint: "Diferencia entre procesar sintaxis y entender significado."
          }
        ],
        quiz: {
          question: "¿A qué se refiere el término 'Qualia' en filosofía de la mente?",
          options: [
            "A la cantidad de memoria RAM disponible",
            "A las cualidades subjetivas y fenomenológicas de las experiencias conscientes (ej. la rojez del rojo)",
            "A un error sintáctico de compilación",
            "A un algoritmo de búsqueda binaria"
          ],
          correct_answer: 1,
          explanation: "Los qualia son las vivencias puramente cualitativas y privadas que no pueden reducirse enteramente a descripciones físicas objetivas."
        }
      }
    ]
  },
  {
    id: "world_dist",
    title: "Sistemas Distribuidos & Algoritmos de Consenso",
    filename: "Sistemas_Distribuidos_Consenso.pdf",
    discipline: "Ingeniería de Software",
    spineColor: "cyan",
    description: "Teorema CAP, tolerancia a fallas por partición de red y algoritmos de consenso distribuido Paxos y Raft.",
    filesize: "3.1 MB",
    status: "stored",
    metadatos: {
      document_id: "world_dist",
      tiempo_estudio: "14 min",
      perfil: "advanced",
      formato: "PDF"
    },
    sections: [
      {
        id: "sec_dist_1",
        title: "Teorema CAP y Algoritmo Raft",
        summary: "Garantías de consistencia linealizable frente a disponibilidad continua ante particiones de red inevitables.",
        key_concepts: ["Teorema CAP", "Consenso Raft", "Quorum", "Replicación de Logs"],
        flashcards: [
          {
            front: "¿Qué postula el teorema CAP de Eric Brewer?",
            back: "En un sistema distribuido con partición de red (P), solo es posible garantizar Consistencia estricta (C) o Disponibilidad (A), pero no ambas simultáneamente.",
            didactic_hint: "Consistency, Availability, Partition tolerance."
          }
        ],
        quiz: {
          question: "¿Cómo resuelve el algoritmo Raft la elección de un nuevo nodo líder cuando el actual cae?",
          options: [
            "Mediante temporizadores aleatorizados de elección y votos por mayoría absoluta (Quorum)",
            "Apagando todos los nodos del cluster simultáneamente",
            "Pidiéndole permiso a un servidor centralizado externo",
            "Eliminando la base de datos de logs"
          ],
          correct_answer: 0,
          explanation: "Raft usa 'randomized election timeouts' para evitar divisiones de votos simultáneas y exige mayoría de nodos activos."
        }
      }
    ]
  }
];
