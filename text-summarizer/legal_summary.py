import spacy
from transformers import T5Tokenizer, T5ForConditionalGeneration
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def combined_summary(text, extractive_sentences=3, max_length=150):

    #loading the spacy model
    nlp = spacy.load("en_core_web_sm")
    #processing the text
    doc = nlp(text)

    # Extractive text summarization -->

    sentences = list(doc.sents)
    if len(sentences) < 2:
        return text

    # compute sentence embeddings
    sentence_embeddings = np.array([sent.vector for sent in doc.sents])

    # compute cosine similarity matrix
    sim_matrix = cosine_similarity(sentence_embeddings)

    # compute sentence scores
    scores = np.sum(sim_matrix, axis=1)

    # ranking the sentences
    ranked_sentences = sorted(((scores[i], sent) for i, sent in enumerate(doc.sents)), reverse=True)
    # select sentences
    extractive_summary = " ".join([sent.text for score, sent in ranked_sentences[:extractive_sentences]])

    # Abstractive text Summarization -->
    preprocessed_text = " ".join(
        [token.text for token in nlp(extractive_summary) if not token.is_punct or token.text in ['.', ',', ';']])

    #Selecting the model
    model = "t5-base"
    tokenizer = T5Tokenizer.from_pretrained(model)
    model = T5ForConditionalGeneration.from_pretrained(model)

    #Summarizing the results based on the extractive summary
    input_text = "summarize: " + preprocessed_text
    inputs = tokenizer.encode(input_text, return_tensors="pt", max_length=512, truncation=True)
    summary_ids = model.generate(inputs, max_length=max_length, min_length=50, length_penalty=2.0, num_beams=4,
                                 early_stopping=True)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary

