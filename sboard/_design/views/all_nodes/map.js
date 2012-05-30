function(doc) {
    if (doc.created && doc.doc_type && doc.importance > 0) {
        emit(doc.created, null);
    }
}
