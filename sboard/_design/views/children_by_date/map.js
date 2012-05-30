function(doc) {
    if (doc.parent && doc.importance > 0) {
        emit([doc.parent, doc.created], null);
    }
    else if (doc.created && doc.doc_type && doc.importance > 0) {
        emit(["~", doc.created], null);
    }
}
