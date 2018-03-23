"""
Copyright 2017 Neural Networks and Deep Learning lab, MIPT

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import Type

import numpy as np

from deeppavlov.core.common.registry import register
from deeppavlov.core.common.log import get_logger
from deeppavlov.core.models.component import Component
from deeppavlov.models.vectorizers.hashing_tfidf_vectorizer import HashingTfIdfVectorizer

logger = get_logger(__name__)


@register("tfidf_ranker")
class TfidfRanker(Component):

    def __init__(self, vectorizer: Type = HashingTfIdfVectorizer, **kwargs):
        self.vectorizer = vectorizer

        if self.vectorizer.load_path.exists():
            self.tfidf_matrix, opts = self.vectorizer.load()
            self.ngram_range = opts['ngram_rage']
            self.hash_size = opts['hash_size']
            self.term_freqs = opts['term_freqs'].squeeze()
            self.doc2index = opts['doc2index']

            self.vectorizer.doc2index = self.doc2index
            self.vectorizer.freqs = self.term_freqs
            self.vectorizer.hash_size = self.hash_size

            self.index2doc = self.get_index2doc()
        else:
            logger.warning("TfidfRanker wasn't initialized, is waiting for training.")

    def get_index2doc(self):
        return dict(zip(self.doc2index.values(), self.doc2index.keys()))

    def __call__(self, question, n=5):
        """
        Rank documents and return top k documents with scores.
        :param question: a query to search an answer for
        :param n: a number of documents to return
        :return: document ids, document scores
        """
        if isinstance(question, list):
            question = question[0]

        q_tfidf = self.vectorizer(question)

        scores = q_tfidf * self.tfidf_matrix

        if len(scores.data) <= n:
            o_sort = np.argsort(-scores.data)
        else:
            o = np.argpartition(-scores.data, n)[0:n]
            o_sort = o[np.argsort(-scores.data[o])]

        doc_scores = scores.data[o_sort]
        doc_ids = [self.index2doc[i] for i in scores.indices[o_sort]]
        return doc_ids, doc_scores

    def fit_batch(self, iterator):
        self.vectorizer.doc2index = iterator.doc2index
        for x, y in iterator.gen_batch():
            self.vectorizer.fit_batch(x, y)

    def save(self):
        self.vectorizer.save()


