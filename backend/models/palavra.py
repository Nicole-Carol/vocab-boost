# models/palavra.py

class Palavra:
    def __init__(self, termo, traducao="", contexto="", gramatica="", pronuncia="",
                 ultima_revisao=None, intervalo=0, facilidade=2.5, pontos=0, deck_id=None):
        self.termo = termo.strip().lower()
        self.traducao = traducao
        self.contexto = contexto
        self.gramatica = gramatica
        self.pronuncia = pronuncia
        self.ultima_revisao = ultima_revisao      # datetime ou None
        self.intervalo = intervalo                # dias (int)
        self.facilidade = facilidade              # float (padrão 2.5)
        self.pontos = pontos                      # pontos acumulados
        self.deck_id = deck_id                    # ID do deck (opcional)
        self.id = None

    def to_dict(self):
        return {
            "id": self.id,
            "termo": self.termo,
            "traducao": self.traducao,
            "contexto": self.contexto,
            "gramatica": self.gramatica,
            "pronuncia": self.pronuncia,
            "ultima_revisao": self.ultima_revisao.isoformat() if self.ultima_revisao else None,
            "intervalo": self.intervalo,
            "facilidade": self.facilidade,
            "pontos": self.pontos,
            "deck_id": self.deck_id
        }

    def __str__(self):
        return f"Palavra({self.termo} → {self.traducao})"