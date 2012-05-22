function(doc) {
    if (doc.parent) {
        emit([doc.parent, doc.created], null);
    }
    else if (doc.created && doc.doc_type) {
        emit(["~", doc.created], null);
    }
}
