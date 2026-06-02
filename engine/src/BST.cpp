#include "BST.h"

BST::BST() : root(nullptr) {}

BST::~BST() {
    clear();
}

void BST::clear() {
    destroy(root);
    root = nullptr;
}

void BST::destroy(BSTNode* node) {
    if (node == nullptr) {
        return;
    }
    destroy(node->left);
    destroy(node->right);
    delete node;
}

int BST::compare(int node_id_a, int degree_a, int node_id_b, int degree_b) const {
    if (degree_a < degree_b) return -1;
    if (degree_a > degree_b) return 1;
    if (node_id_a < node_id_b) return -1;
    if (node_id_a > node_id_b) return 1;
    return 0;
}

BSTNode* BST::insertRec(BSTNode* node, int node_id, int degree) {
    if (node == nullptr) {
        BSTNode* created = new BSTNode;
        created->degree = degree;
        created->node_id = node_id;
        created->left = nullptr;
        created->right = nullptr;
        return created;
    }

    int cmp = compare(node_id, degree, node->node_id, node->degree);
    if (cmp < 0) {
        node->left = insertRec(node->left, node_id, degree);
    } else if (cmp > 0) {
        node->right = insertRec(node->right, node_id, degree);
    }
    return node;
}

BSTNode* BST::findMin(BSTNode* node) {
    while (node != nullptr && node->left != nullptr) {
        node = node->left;
    }
    return node;
}

BSTNode* BST::removeRec(BSTNode* node, int node_id, int degree) {
    if (node == nullptr) {
        return nullptr;
    }

    int cmp = compare(node_id, degree, node->node_id, node->degree);
    if (cmp < 0) {
        node->left = removeRec(node->left, node_id, degree);
    } else if (cmp > 0) {
        node->right = removeRec(node->right, node_id, degree);
    } else {
        if (node->left == nullptr) {
            BSTNode* right = node->right;
            delete node;
            return right;
        }
        if (node->right == nullptr) {
            BSTNode* left = node->left;
            delete node;
            return left;
        }

        BSTNode* successor = findMin(node->right);
        node->node_id = successor->node_id;
        node->degree = successor->degree;
        node->right = removeRec(node->right, successor->node_id, successor->degree);
    }
    return node;
}

void BST::insert(int node_id, int degree) {
    root = insertRec(root, node_id, degree);
}

void BST::remove(int node_id, int degree) {
    root = removeRec(root, node_id, degree);
}

void BST::update(int node_id, int old_deg, int new_deg) {
    remove(node_id, old_deg);
    insert(node_id, new_deg);
}

void BST::findMaxRec(BSTNode* node, int& best_id, int& best_degree) const {
    if (node == nullptr) {
        return;
    }
    findMaxRec(node->left, best_id, best_degree);
    if (node->degree > best_degree || (node->degree == best_degree && node->node_id > best_id)) {
        best_degree = node->degree;
        best_id = node->node_id;
    }
    findMaxRec(node->right, best_id, best_degree);
}

int BST::findMax() const {
    int best_id = -1;
    int best_degree = -1;
    findMaxRec(root, best_id, best_degree);
    return best_id;
}
