function(doc) {
    if (doc.doc_type == 'Comment' && doc.parents && doc.parents.length > 0) {
        emit([doc.parents[doc.parents.length-1], doc.created], null);
    }
}
