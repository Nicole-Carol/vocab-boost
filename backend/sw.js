const CACHE_NAME = 'pdf-reader-v4';
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/style.css',
    // Adicione outros estáticos se necessário
];

// Lista de origens/URLs que NÃO devem ser interceptadas (permitir fetch direto)
const EXCLUDED_PATHS = [
    'cdnjs.cloudflare.com',
    'cdn.jsdelivr.net',
    'api.dictionaryapi.dev',
    'api.datamuse.com'
];

// Verifica se a requisição deve ser ignorada pelo Service Worker
function shouldSkipFetch(request) {
    const url = new URL(request.url);
    return EXCLUDED_PATHS.some(domain => url.hostname.includes(domain));
}

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(err => {
                console.error('Cache addAll failed:', err);
            });
        })
    );
    self.skipWaiting(); // Ativa o novo SW imediatamente
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim(); // Toma controle imediato
});

self.addEventListener('fetch', (event) => {
    // Se a requisição for para CDNs ou APIs externas, deixa passar direto (sem cache)
    if (shouldSkipFetch(event.request)) {
        return; // O navegador faz o fetch normalmente
    }

    const url = new URL(event.request.url);

    // Para chamadas à sua própria API (backend)
    if (url.pathname.startsWith('/analisar') || 
        url.pathname.startsWith('/traduzir-frase') ||
        url.pathname.startsWith('/adicionar-palavra') || 
        url.pathname.startsWith('/revisar') ||
        url.pathname.startsWith('/palavras') || 
        url.pathname.startsWith('/decks') ||
        url.pathname.startsWith('/estatisticas') ||
        url.pathname.startsWith('/dashboard') ||
        url.pathname.startsWith('/progresso') ||
        url.pathname.startsWith('/salvar-frase') ||
        url.pathname.startsWith('/frases-por-deck') ||
        url.pathname.startsWith('/adicionar-regra') ||
        url.pathname.startsWith('/regras-gramaticais') ||
        url.pathname.startsWith('/verificar-regras')) {
        
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    // Opcional: cachear a resposta para uso offline (descomente se quiser)
                    // const clone = response.clone();
                    // caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return response;
                })
                .catch(() => {
                    return new Response(
                        JSON.stringify({ erro: 'Você está offline. Esta ação requer internet.' }),
                        { headers: { 'Content-Type': 'application/json' } }
                    );
                })
        );
        return;
    }

    // Para recursos estáticos (HTML, CSS, JS local, imagens)
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(event.request).then(response => {
                // Só armazena respostas bem-sucedidas (200)
                if (response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            }).catch(() => {
                if (event.request.mode === 'navigate') {
                    return caches.match('/');
                }
                return new Response('Recurso não disponível offline.');
            });
        })
    );
});