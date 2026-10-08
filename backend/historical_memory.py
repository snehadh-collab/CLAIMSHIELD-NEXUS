import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class HistoricalCaseMemory:

    def __init__(self, claims_csv_path="synthetic_claims.csv"):
        self.df = pd.read_csv(claims_csv_path)
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.case_documents = []
        self.case_ids = []
        self._build_memory_index()

    def _build_memory_index(self):
        """Creates searchable document strings combining claim details, flags, and provider info."""
        for _, row in self.df.iterrows():
            doc = (
                f"Claim ID: {row['claim_id']} | "
                f"Provider: {row['provider_name']} (NPI: {row['provider_npi']}) | "
                f"Member: {row['member_id']} | "
                f"Location: {row['location_city']} | "
                f"Fraud Flag: {row['fraud_flag']} | "
                f"Amount: ${row['claim_amount']} | "
                f"CPT Code: {row['cpt_code']}"
            )
            self.case_documents.append(doc)
            self.case_ids.append(row["claim_id"])

        # Fit TF-IDF Vectorizer
        self.tfidf_matrix = self.vectorizer.fit_transform(self.case_documents)

    def search_similar_precedents(self, query_text, top_k=3):
        """Searches historical cases using TF-IDF cosine similarity for precedent matching."""
        query_vec = self.vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Get top-k match indices
        top_indices = similarities.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            results.append(
                {
                    "case_id": self.case_ids[idx],
                    "match_score": round(float(similarities[idx]), 4),
                    "summary": self.case_documents[idx],
                }
            )
        return results


if __name__ == "__main__":
    memory = HistoricalCaseMemory()
    print("Historical Case Memory Indexer Ready.")

    # Test query
    sample_query = "Phantom billing non-existent ghost members in Chennai"
    precedents = memory.search_similar_precedents(sample_query)

    print(f"\nTop Precedent Case Matches for Query: '{sample_query}'")
    for match in precedents:
        print(f"Case ID: {match['case_id']} | Score: {match['match_score']}")
        print(f"Summary: {match['summary']}\n")