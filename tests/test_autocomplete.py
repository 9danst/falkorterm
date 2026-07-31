from falkorterm.widgets.cypher_area import SchemaTokens, suggest_completion


def test_suggest_completion_basic_prefix():
    tokens = SchemaTokens(labels=("Person", "Movie"), relations=("KNOWS",))
    assert suggest_completion("MATCH (n:Per", 12, tokens) == "son"
    assert suggest_completion("MATCH (n:Person", 15, tokens) == ""


def test_suggest_completion_relation_context():
    tokens = SchemaTokens(labels=("Person",), relations=("KNOWS", "LIKES"))
    text = "MATCH ()-[r:KN"
    assert suggest_completion(text, len(text), tokens) == "OWS"


def test_suggest_completion_property_context():
    tokens = SchemaTokens(properties=("name", "age"))
    text = "RETURN n.na"
    assert suggest_completion(text, len(text), tokens) == "me"


def test_suggest_completion_all_tokens_elsewhere():
    tokens = SchemaTokens(labels=("Person",), relations=("KNOWS",), properties=("name",))
    text = "MATCH (n) WHERE Per"
    assert suggest_completion(text, len(text), tokens) == "son"


def test_suggest_completion_empty_prefix():
    tokens = SchemaTokens(labels=("Person",))
    assert suggest_completion("MATCH (n:)", 9, tokens) == ""
